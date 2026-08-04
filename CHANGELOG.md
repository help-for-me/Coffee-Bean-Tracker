# Changelog

All notable changes to this project are documented here.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Insights page (0.4.0, built - manual test against your real data still
  needed to close it): average score by process, average score by month,
  and most-repurchased bean profiles with an up/down/flat trend, each with
  a "Recent" vs. "All time" toggle once there's enough history for a
  recent window. Backend is a pure, DB-backed stats module
  (`backend/insights/stats.py`) behind `GET /insights`; frontend charts
  are hand-rolled inline SVG (no charting library), verified in a real
  browser against seeded data.
- `roast_location` field (where the roaster roasted it, e.g. "Vancouver,
  BC" - distinct from origin_country/region, which is where it was
  grown), extracted alongside the other bag-printed attributes and
  typeable manually.
- Multi-farm support: a new `entry_farms` table for bags/blends that list
  more than one distinct farm, each with its own location. Shown on Entry
  Detail as a new "Farms" section. `farm_producer` stays as a simple
  single-value summary field for backward compatibility.
- A real database migration mechanism (`PRAGMA user_version` in
  `database.py`) - previously `init_db()` only ran `schema.sql` against a
  brand-new database file, so schema changes never reached an
  already-deployed, already-populated database like Iron's. This is the
  first schema change to land after a real deployment existed, so the gap
  needed closing now; the migration itself is purely additive.

### Fixed
- Extraction accuracy (0.2.1): two real bags exposed field-misfiling, not
  outright failure - variety and process words ("Castillo", "Honey") landing in `printed_tasting_notes`
  instead of their own fields, a farm name landing in `region` instead of
  `farm_producer`, and co-ferment wording getting redundantly appended to
  `process`. Fixed with a coffee vocabulary reference embedded in the
  extraction prompt (`backend/extractor/coffee_vocab.py`), explicit
  field-boundary guidance, and defensive post-processing that strips
  leaked co-ferment wording and corrects small typos against known terms.
  Confirmed fixed against both real bags after redeploying.
- Insights tab showed stale placeholder text referencing milestone 0.3.0
  (from before 0.3.0/0.4.0 were reordered) instead of 0.4.0.
- README's `PHOTOS_PATH` default was still the old Docker-only absolute
  path, out of sync with the actual `.env.example` default.
- Export tab claimed "CSV export arrives in milestone 0.4.0," but CSV
  export was never actually scoped into 0.4.0 (Insights only covers stats
  and charts) or any other milestone - placeholder corrected to not claim
  a specific milestone; needs an actual roadmap slot decided.

### Changed
- Roadmap: added viewing an entry's uploaded photo(s), and browsing other
  photos of the same bean for comparison, to 1.1.0 - corrected from an
  earlier assumption that the second part needs fuzzy matching (it
  doesn't; `bean_profile_id` already groups entries exactly). Added
  MAJOR 3 (iOS offline-first companion app) and MAJOR 4 (on-device AI/OCR)
  as concept-stage future phases.

## [0.3.0] - 2026-08-04

### Added
- Multi-stage Dockerfile: compiles the React frontend and serves it from
  the same FastAPI container as the API.
- `batch_number` field (bag-printed roast/lot number), extracted alongside
  the other bag-printed attributes.
- Entry Detail page: tap an entry in History to see every bag detail
  (explicit "Not identified" for anything not filled in) and every rating
  logged against it, not just the latest.
- Deployed and running on the primary Docker host via Unraid, LAN-only.
  Confirmed reachable and confirmed data survives a container restart.

### Changed
- Roadmap: missing Unraid WebUI quick-launch button noted as a 0.3.1 fix
  (needs the template's `<WebUI>` field, which the manual container setup
  doesn't have). Human-readable photo filenames and an Anthropic API key
  expiry reminder added as tracked items.

## [0.2.0] - 2026-08-04

### Added
- Photo upload on New Entry, with instant save and background extraction
  (`extraction_status`: pending -> complete/failed, never stuck).
- `ClaudeExtractor` using the Anthropic API, plus a swappable factory
  (Ollama reserved for 1.6.0).
- `batch_number` field (bag-printed roast/lot number), extracted alongside
  the other bag-printed attributes and typeable manually.
- `ROADMAP.md` with full per-milestone detail (deployment specifics,
  manual test criteria) - README keeps just the checklist now.
- `private/` folder (gitignored) for infra notes that shouldn't be public
  (hostnames, hardware specs).
- Milestone 0.5.0 added to the roadmap: photo-first identity (no typed
  roaster/bean name required when a photo's attached) - planned, not built.

### Changed
- Split milestone 0.3.0 into 0.3.0 (deploy on the primary Docker host)
  and 0.3.1 (deployment polish), so something real running on real
  hardware lands before the nice-to-haves.
- README screenshot removed.

### Fixed
- `.env` was never actually loaded outside Docker - `docker-compose`'s
  `env_file:` did it automatically, but local `uvicorn --reload` had
  nothing wiring `.env` into the process, so `ANTHROPIC_API_KEY` (and
  everything else in `.env`) was silently ignored.
- `PHOTOS_PATH` in `.env.example` used a Docker-only absolute path,
  which would have broken local photo storage once `.env` actually
  started loading.
- Extraction crashed on a real Claude response: `response.content[0].text`
  isn't always where the answer lives (a response can have multiple
  content blocks) - now collects every text block, and defensively
  strips a markdown fence if the model adds one.
- Extraction success was silent in the logs (only failures logged
  anything); both now log, and INFO-level logging is actually enabled
  (Python's default level would have swallowed it either way).

## [0.1.0] - 2026-08-03

### Added
- Full SQLite schema, every table from the spec including ones unused until later milestones.
- Backend: entry and rating creation, entry listing, roaster/bean-name autocomplete,
  "rate a previous bean" endpoint.
- Frontend: React + Tailwind app, mobile-first, bottom tab bar (Home/History/Insights/Export).
- New Entry flow, History list, Rate a Previous Bean flow.
- Project docs: README, LICENSE (MIT), CHANGELOG, CLAUDE.md.
- Repo scaffolding: Docker/Compose, GHCR publish workflow, .env.example.

### Changed
- Roadmap: self-hosted Unraid template noted under 0.4.0, data export/import (JSON)
  added as 1.10.0, "Future ideas" section added for the Unraid CA feed and Proxmox
  Helper-Scripts community submissions.

### Fixed
- GHCR publish workflow: image tags must be lowercase.
