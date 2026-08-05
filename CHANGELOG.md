# Changelog

All notable changes to this project are documented here.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security
- Fixed the static-file fallback route so it can no longer resolve or
  serve a path outside the intended frontend build directory.
- Photo uploads are now checked against a real image signature (not just
  the filename or claimed content-type) and capped in size and count per
  entry.
- API error responses no longer include internal exception text - the
  full detail is logged server-side, and the client gets a generic
  message instead.
- Added a short per-client cooldown to the AI-backed endpoints (re-run
  extraction, generate insights summary) so a stuck client or repeated
  retries can't spend the Anthropic API key's quota unchecked.

## [0.9.0] - 2026-08-04

### Added
- AI narrative insights: an "Insights summary" section on the Insights
  page generates a short, actionable recommendation from your own logged
  data (e.g. "you consistently rate Honey-process Colombian coffees
  highest - look for those"), not just a recap of numbers already on the
  page. Backed by a provider-agnostic `InsightGenerator` interface
  (`NARRATIVE_PROVIDER` env var, mirrors the extraction provider setup),
  cached per time-window in the database so it doesn't regenerate on
  every page load.

## [0.8.0] - 2026-08-04

### Added
- Fuzzy repurchase matching: typos no longer create duplicate bean
  profiles or get missed by autocomplete. New Entry's autocomplete now
  surfaces close matches (not just exact prefixes), and AI extraction
  correctly merges OCR-typo'd identity (e.g. "Jairo Aroila" vs "Jario
  Arcila") into the existing profile instead of creating a second one -
  closing the gap the 0.5.1 real-world test found. Uses a conservative
  similarity threshold for the automatic merge case specifically, so two
  different roasters with similar names are never silently combined.

## [0.7.0] - 2026-08-04

### Added
- Entry Detail now shows the photo(s) actually uploaded for that entry,
  plus photos from other entries of the same bean (same
  `bean_profile_id`) for comparison against a blurry or bad shot. Served
  via `GET /photos/{id}`, keyed off the `entry_photos` primary key so the
  file path is never client-supplied.
- "Re-run AI extraction" button on Entry Detail
  (`POST /entries/{id}/reextract`) - re-triggers extraction against the
  entry's own saved photos in the background, for cases where a prompt
  fix or a retry might do better the second time.
- Real edit/delete UI for saved entries and ratings: bag-detail fields
  and ratings can now be corrected or removed after the fact
  (`PATCH`/`DELETE /entries/{id}`, `PATCH`/`DELETE
  /entries/{id}/ratings/{rating_id}`), closing the "fast one-way log"
  gap from 0.1.0. Entry deletion cascades its ratings, photos, and farm
  rows and removes photo files from disk, not just their DB rows.

### Fixed
- Bilingual packaging text (e.g. "Whole Bean Coffee / Grains de café" on
  a Canadian bag) no longer leaks into `printed_tasting_notes` -
  extraction prompt now explicitly excludes it as a product-type label.

## [0.6.0] - 2026-08-04

### Added
- Exportable application logs: logs now write to a rotating file under
  the already-mounted `data/` volume (5MB cap, 3 backups) alongside the
  existing stdout logging, so they survive restarts and are grabbable
  directly from Unraid's file browser instead of the Docker UI's Logs
  panel. Prompted directly by a 0.5.1 test attempt where an extraction
  failure could only be diagnosed via a screenshot conversation.

## [0.5.0] - 2026-08-04

### Added
- Photo-first identity: a bag entry can now be saved with just a photo
  and no typed roaster/bean name. A provisional bean profile
  ("Unidentified") gets created immediately and either renamed in place
  or merged into an existing profile once extraction resolves a real
  identity - `entries.bean_profile_id` stays `NOT NULL` throughout, no
  schema constraint change. Cafe cups still always require typed
  identity. Extraction prompt now attempts roaster/bean name alongside
  everything else, but a typed name is never overwritten.
- 0.5.1 real-world manual test passed: instant save and correct identity
  resolution confirmed on an actual phone with a real bag. Also confirmed
  the known exact-match limitation (deferred to 0.8.0's fuzzy matching) -
  the same bag logged under slightly different OCR'd text created a
  second profile instead of merging.

### Fixed
- Export tab said "not currently scheduled to a specific milestone" -
  CSV export (alongside XLSX and GitHub backup) now has a real home in
  1.1.0, so it's actually tracked instead of left as an orphaned gap.

## [0.4.0] - 2026-08-04

### Added
- Insights page: average score by month, favourite processes/origin
  countries/tasting notes (ranked by average score - tasting notes are
  tokenized from free text, comma- or dash-separated depending on the
  roaster, and deduped case-insensitively), and most-repurchased bean
  profiles with an up/down/flat trend, each with a "Recent" vs. "All time"
  toggle once there's enough history for a recent window. Deliberately
  keeps process separate from co-ferment status for now (own future
  cross-reference). Backend is a pure, DB-backed stats module
  (`backend/insights/stats.py`) behind `GET /insights`; frontend charts
  are hand-rolled inline SVG (no charting library), verified in a real
  browser against seeded data. Manual test passed against real entries.
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
  photos of the same bean for comparison, to 0.7.0 - corrected from an
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
  (Ollama reserved for 1.3.0).
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
  added as 1.7.0, "Future ideas" section added for the Unraid CA feed and Proxmox
  Helper-Scripts community submissions.

### Fixed
- GHCR publish workflow: image tags must be lowercase.
