import pytest

from backend import crud
from backend.models import EntryCreate


def _seed_entry(conn, roaster="Stumptown", bean_name="Hair Bender", score=8):
    entry_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster=roaster, bean_name=bean_name, score=score)
    )
    return entry_id


# --- get_full_export ---


def test_get_full_export_empty_database_has_every_table_as_empty_list(conn):
    export = crud.get_full_export(conn)
    assert export["format_version"] == 1
    assert "exported_at" in export
    for table in (
        "bean_profiles", "bean_profile_enrichment", "entries", "entry_farms", "entry_photos",
        "ratings", "insight_narratives", "settings",
    ):
        assert export[table] == []


def test_get_full_export_includes_created_data(conn):
    _seed_entry(conn, roaster="Monogram", bean_name="Mango", score=9)
    export = crud.get_full_export(conn)
    assert len(export["bean_profiles"]) == 1
    assert export["bean_profiles"][0]["roaster"] == "Monogram"
    assert len(export["entries"]) == 1
    assert len(export["ratings"]) == 1
    assert export["ratings"][0]["score"] == 9


# --- import_full_export: validation ---


def test_import_rejects_wrong_format_version(conn):
    with pytest.raises(crud.ImportValidationError, match="format_version"):
        crud.import_full_export(conn, {"format_version": 99})


def test_import_rejects_missing_format_version(conn):
    with pytest.raises(crud.ImportValidationError):
        crud.import_full_export(conn, {})


def test_import_rejects_unknown_column(conn):
    payload = {"format_version": 1, "bean_profiles": [{"id": 1, "roaster": "X", "bean_name": "Y", "evil": "; DROP TABLE entries; --"}]}
    with pytest.raises(crud.ImportValidationError, match="Unknown column"):
        crud.import_full_export(conn, payload)


def test_import_rejects_non_dict_row(conn):
    payload = {"format_version": 1, "bean_profiles": ["not-a-dict"]}
    with pytest.raises(crud.ImportValidationError):
        crud.import_full_export(conn, payload)


def test_import_rejects_non_list_table(conn):
    payload = {"format_version": 1, "bean_profiles": {"id": 1}}
    with pytest.raises(crud.ImportValidationError):
        crud.import_full_export(conn, payload)


def test_import_validation_failure_leaves_existing_data_untouched(conn):
    _seed_entry(conn, roaster="Stumptown")
    payload = {"format_version": 1, "bean_profiles": [{"id": 99, "roaster": "X", "bean_name": "Y", "evil": "oops"}]}
    with pytest.raises(crud.ImportValidationError):
        crud.import_full_export(conn, payload)
    assert crud.get_counts(conn)["entries"] == 1


# --- import_full_export: behaviour ---


def test_import_replaces_existing_data(conn):
    _seed_entry(conn, roaster="Old Roaster")
    payload = {
        "format_version": 1,
        "bean_profiles": [{"id": 1, "roaster": "New Roaster", "bean_name": "New Bean", "is_provisional": 0}],
        "entries": [{
            "id": 1, "bean_profile_id": 1, "entry_type": "bag", "extraction_status": "not_applicable",
            "extraction_source": "manual", "currency": "CAD", "co_ferment_status": "unknown",
        }],
        "ratings": [{"id": 1, "entry_id": 1, "score": 7}],
    }
    counts = crud.import_full_export(conn, payload)
    assert counts == {"entries": 1, "ratings": 1, "photos": 0}
    entries = crud.list_entries(conn)
    assert len(entries) == 1
    assert entries[0]["roaster"] == "New Roaster"


def test_import_round_trip_preserves_ids_and_content(conn):
    entry_id = _seed_entry(conn, roaster="Pallet Coffee", bean_name="Elkin Guzman", score=9)
    exported = crud.get_full_export(conn)

    counts = crud.import_full_export(conn, exported)

    assert counts["entries"] == 1
    entry = crud.get_entry(conn, entry_id)
    assert entry is not None  # same id still resolves after the round trip
    assert entry["bean_profile"]["roaster"] == "Pallet Coffee"
    assert entry["ratings"][0]["score"] == 9


def test_import_round_trip_preserves_enrichment_and_website_description(conn):
    # Surfaced by merging 1.9.0 (roaster website enrichment) into the
    # tracking branch alongside 1.7.0 (this export/import feature) - the
    # bean_profile_enrichment table and entries.website_description column
    # didn't exist yet when 1.7.0's _EXPORT_TABLES allowlist was written.
    entry_id = _seed_entry(conn, roaster="Funk Coffee", bean_name="Here Comes the Flood", score=9)
    bean_profile_id = crud.get_entry(conn, entry_id)["bean_profile"]["id"]
    crud.update_entry(conn, entry_id, {"website_description": "A juicy, floral Kenyan filter roast."})
    crud.confirm_enrichment(
        conn, bean_profile_id, url="https://funkcoffee.ca/x", title="X", source_path=None, fields={}
    )

    exported = crud.get_full_export(conn)
    assert len(exported["bean_profile_enrichment"]) == 1

    counts = crud.import_full_export(conn, exported)

    assert counts["entries"] == 1
    entry = crud.get_entry(conn, entry_id)
    assert entry["website_description"] == "A juicy, floral Kenyan filter roast."
    assert entry["bean_profile"]["enrichment"]["status"] == "confirmed"
    assert entry["bean_profile"]["enrichment"]["source_url"] == "https://funkcoffee.ca/x"


def test_import_empty_payload_wipes_all_data(conn):
    _seed_entry(conn)
    crud.import_full_export(conn, {"format_version": 1})
    assert crud.get_counts(conn) == {"entries": 0, "ratings": 0, "photos": 0}


def test_import_restores_settings_table(conn):
    # No settings CRUD helper exists on this branch yet (that's 1.4.0's
    # Settings UI milestone, built separately) - the settings table itself
    # has been in schema.sql since 0.1.0 though, so write to it directly.
    with conn:
        conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("recent_window_months", "4"))
    exported = crud.get_full_export(conn)
    with conn:
        conn.execute("UPDATE settings SET value = ? WHERE key = ?", ("99", "recent_window_months"))

    crud.import_full_export(conn, exported)

    row = conn.execute("SELECT value FROM settings WHERE key = ?", ("recent_window_months",)).fetchone()
    assert row["value"] == "4"
