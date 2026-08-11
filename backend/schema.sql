-- The product identity: roaster + name. Normally known at submit time
-- (typed or autocompleted) and resolved synchronously, never waiting on
-- AI. Since 0.5.0, a bag entry submitted with only a photo gets a
-- provisional row here (is_provisional = 1, roaster = "Unidentified")
-- instead - renamed in place, or merged into an existing profile, once
-- extraction resolves a real identity.
CREATE TABLE bean_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roaster TEXT NOT NULL,
    bean_name TEXT NOT NULL,
    is_provisional INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per coffee "instance" — a bag you bought, OR a single cup you had
-- somewhere. Saved immediately on submit; detail fields fill in later by
-- background extraction once photo upload is built in 0.2.0 (or typed
-- manually before that).
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bean_profile_id INTEGER NOT NULL REFERENCES bean_profiles(id),
    user_id INTEGER REFERENCES users(id),   -- unused until 1.5.0 multi-user
    entry_type TEXT NOT NULL,       -- 'bag' or 'cafe_cup'
    cafe_name TEXT,                  -- only relevant for entry_type = 'cafe_cup'
    entry_date DATE,
    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    price_paid REAL,
    currency TEXT DEFAULT 'CAD',

    extraction_status TEXT DEFAULT 'not_applicable',  -- 'pending' (photos submitted, awaiting background job) / 'complete' / 'failed' / 'not_applicable' (no photos, fully manual)
    extraction_source TEXT,          -- 'claude' or 'manual'

    origin_country TEXT,
    region TEXT,
    farm_producer TEXT,
    altitude_m INTEGER,
    variety TEXT,                    -- e.g. Bourbon, Typica, Geisha
    process TEXT,                     -- washed, natural, honey, anaerobic, etc.
    co_ferment_status TEXT DEFAULT 'unknown',   -- 'yes' / 'no' / 'unknown'
    co_ferment_ingredient TEXT,       -- e.g. 'lychee', 'cascara', 'wine yeast' — populated when co_ferment_status = 'yes' and the label names it
    certifications TEXT,              -- organic, fair trade, direct trade, etc.
    roast_level TEXT,                 -- light, medium, medium-dark, dark
    printed_tasting_notes TEXT,       -- flavor notes from the bag/menu/info card
    roast_date DATE,
    bag_weight_g INTEGER,
    batch_number TEXT,                -- roast/lot number, when the bag prints one
    roast_location TEXT,              -- where the ROASTER roasted it, e.g. "Vancouver, BC" — not where it was grown (that's origin_country/region)
    website_description TEXT,         -- roaster's own descriptive copy about this coffee, from 1.9.0 website enrichment (never printed on a label, so kept distinct from printed_tasting_notes)

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Farms/producers contributing to this entry. Most entries have exactly
-- one row here; a blend that names more than one distinct farm gets one
-- row per farm. farm_producer on entries stays as a simple summary
-- (backward-compatible single-value display); this is where each farm's
-- own location lives when the label prints it.
CREATE TABLE entry_farms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    farm_name TEXT NOT NULL,
    location TEXT
);

-- Any number of photos per entry. Table exists from 0.1.0, first used in
-- 0.2.0 once photo upload is built.
CREATE TABLE entry_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    photo_path TEXT NOT NULL,
    upload_order INTEGER,
    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per rating EVENT. An entry can have several (revisit a bag,
-- reorder the same cafe drink).
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    user_id INTEGER REFERENCES users(id),   -- unused until 1.5.0 multi-user

    score REAL NOT NULL,             -- 0-10, required
    narrative_notes TEXT,            -- optional free text

    -- Advanced / optional, collapsed by default in the UI:
    acidity_score REAL,
    body_score REAL,
    sweetness_score REAL,
    brew_style TEXT,                  -- 'Pour Over' (default), 'Espresso', 'French Press', 'Cafe-made', 'Other'
    repurchase TEXT,                  -- yes / no / maybe

    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP    -- unused until 0.7.0 edit support
);

-- Unused until 1.5.0 multi-user/auth.
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unused until 1.4.0 Settings UI.
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Unused until 1.1.0 data backup sinks. Tracks last successful export per sink.
CREATE TABLE export_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sink TEXT NOT NULL,              -- 'local_xlsx' or 'github'
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT                       -- 'success' or 'failed'
);

-- Unused until 0.9.0 AI narrative insights. Caches generated summaries.
CREATE TABLE insight_narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_type TEXT,                -- 'all_time' or 'recent'
    summary_text TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unused until 1.9.0 roaster website enrichment. One row per bean_profile,
-- created the first time a lookup is attempted (a missing row means "never
-- attempted yet" - see crud.maybe_start_enrichment). Never more than one
-- row per profile; a reprocess resets this row in place rather than adding
-- a new one.
CREATE TABLE bean_profile_enrichment (
    bean_profile_id INTEGER PRIMARY KEY REFERENCES bean_profiles(id),
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' / 'needs_review' / 'confirmed' / 'no_match' / 'failed'
    candidates TEXT,          -- JSON list of {url, title, snippet}, set only while status = 'needs_review'
    source_url TEXT,          -- the confirmed roaster product page, once status = 'confirmed'
    source_path TEXT,         -- local path to the saved fetched page text (see enrichment_sources.py)
    extra_context TEXT,       -- user-supplied hint from a "none of these" rejection, used by the next lookup
    checked_at TIMESTAMP,     -- when the most recent lookup attempt finished
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
