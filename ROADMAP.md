# Roadmap

Detailed planning for each milestone. For an at-a-glance checklist, see the
[README](README.md#roadmap).

## Versioning policy

Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **MAJOR** - a fundamentally new phase (0 = building the MVP, 1 = stable,
  2 = blank slate, 3 = iOS offline-first companion app, 4 = on-device AI/OCR)
- **MINOR** - new functionality added
- **PATCH** - bug fixes/stabilization, no new features

Patches aren't planned in advance with specific content - they get created
reactively when a manual test (or real use) turns up something that needs
fixing. A minor version's section below may show a patch already released
with what it fixed; until then, "patches TBD as needed" is the honest
answer, not a gap.

**A manual verification pass is the closing gate before every MINOR or
MAJOR bump.** Automated tests (pytest) get written alongside each patch,
not as a separate step - they cover pure logic, not UI flows.

---

## MAJOR 0 - Building the MVP (pre-release)

### 0.1.0 - Foundation ✅ shipped 2026-08-03
Full DB schema (every table, including ones not used until later
milestones), FastAPI skeleton, manual entry creation (roaster/bean-name
autocomplete, rate 0-10, optional narrative, no photo yet), "select a
recent bean to rate again" flow, plain unfiltered entry list.

Manual test (passed): logged an entry by hand, rated it, re-rated a recent
bean, confirmed everything lists correctly, confirmed foreign keys and
displayed counts matched `SELECT COUNT(*)` against the actual SQLite file.

### 0.2.0 - AI/OCR extraction loop ✅ shipped 2026-08-04
Photo upload, `ClaudeExtractor`, background-task wiring, `extraction_status`
lifecycle - fills in bag-printed attributes (origin, process, roast level,
tasting notes, co-ferment) automatically and correctly files them into the
entry.

Manual test (passed): submitted a real bag photo (Monogram Coffee), confirmed
instant save, confirmed the background job correctly filled in and filed
the details, confirmed background job reliability (a missing/bad API key
resolves to `failed`, never stuck `pending`, app never crashes) - covered
by automated pytest cases plus a live browser check and a real-key test
against a real bag.

**0.2.1** - extraction accuracy fix, prompted by a second real bag (Pallet
Coffee - Elkin Guzman) where the model misfiled words instead of failing
outright: "Castillo" (variety) and "Honey" (process) both landed in
`printed_tasting_notes` instead of their own fields, and the farm name
("El Mirado[r]") landed in `region` instead of `farm_producer`. A separate
issue on an earlier bag (Monogram) also showed a producer name leaking
into `region`, and the process field getting "Mango Co-Fermented" appended
to it redundantly with the dedicated co-ferment fields. Fixed by:
- Adding a coffee vocabulary reference (common processes, varieties,
  growing regions - `backend/extractor/coffee_vocab.py`) to the extraction
  prompt, so the model has known terms to check ambiguous label words
  against instead of guessing from position on the label alone.
- Explicit field-boundary guidance in the prompt: region is a sub-national
  growing area, never a person/farm name; process is the base method only,
  never co-ferment wording; tasting notes are flavor descriptors only,
  never variety/process words even when a label line visually groups them
  together.
- Defensive post-processing (`normalize_extraction`): strips any
  co-ferment wording that still leaks into `process`, and corrects small
  typos in `process`/`variety` against the known-terms list (conservative -
  a real but uncommon term is left alone, never remapped to the nearest
  known one).
- Covered by pytest cases built directly from the two real failures above.

Confirmed: re-tested against both real bags (Elkin Guzman, Monogram) with
the updated prompt - variety/process/tasting-notes now split correctly,
region correctly left null instead of guessing a farm name into it.

Also added in 0.2.1: `roast_location` (where the roaster roasted it, e.g.
"Vancouver, BC" - distinct from origin_country/region, which is where it
was grown) and multi-farm support (`entry_farms` table - most bags name
one farm, but a blend can list several, each with its own location).
Since the Iron deployment already has a live populated database, this
needed a real migration path (previously `init_db()` only ever ran
`schema.sql` against a brand-new file) - added via `PRAGMA user_version`
in `database.py`, additive only, covered by a migration test that
simulates the pre-migration schema shape.

### 0.3.0 - Deploy on the primary Docker host
Swapped ahead of Insights, and split from polish, so this one thing happens
first: something real running on real hardware, so every milestone after
this gets tested by clicking "Update" on the deployed container instead of
manually reinstalling dependencies on a laptop each time. Host specifics
(hostname, hardware) live in `private/deployment-notes.md` - gitignored,
never on GitHub.

- **Finish the Dockerfile.** Currently backend-only (a deliberate stub from
  when the frontend didn't exist yet). Needs a real multi-stage build:
  compile the React app (`npm run build`), serve the static files from the
  same FastAPI container as the API (`StaticFiles` mount, added after the
  API routers so specific routes still win).
- **GHCR publish pipeline** - already built and working
  (`.github/workflows/docker-publish.yml`, fixed for lowercase image
  names). Publishes `ghcr.io/help-for-me/coffee-bean-tracker` on every push
  to `main` and on version tags.
- **Deploy it.** Add a container on the primary Docker host pointed at
  `ghcr.io/help-for-me/coffee-bean-tracker:latest`, using the volumes
  already defined in `docker-compose.yml` (`./data`, `./photos`,
  `./exports`).
- **LAN-only.** Bind the port to the LAN, no port-forwarding - the app only
  ever calls out to Claude's API, never accepts inbound traffic from the
  internet.

Manual test closes 0.3.0: it's actually running on the deployed container
and reachable on the LAN. Container restart shouldn't lose data.

0.3.1 ("Deployment polish" - self-hosted Unraid template, front screen/mobile
polish) was retired as its own milestone: 0.3.0 is functional as-is, and
these were nice-to-haves, not blockers. Their two pieces moved to where they
naturally fit long-term - the Unraid template into "Future ideas" below, and
mobile/front-screen polish folded into 1.9.0, which already covers general
UI polish.

### 0.4.0 - Insights
Deterministic stats engine + a couple of fixed charts, built on real data
from 0.1.0 (manual entry) and 0.2.0 (extraction). No AI-generated narrative
summary yet (that's 1.4.0) - just the charts and numbers.

- Average score grouped by `process` (fixed for MVP; more attributes and a
  switcher arrive in 1.5.0)
- Rolling average score by month
- Most-repurchased/reordered bean profiles, and whether score trends up or
  down across repeat entries
- "Recent" window: compare last 4 months vs. last 10 entries, whichever has
  more rated entries (`RECENT_WINDOW_MONTHS` / `RECENT_WINDOW_COUNT` env
  vars, fixed until the 1.7.0 Settings UI). Only applies once there's at
  least 4 months of history *and* at least 10 entries.

Manual test closes 0.4.x: the insights page shows accurate numbers against
real entries.

### 0.5.0 - Photo-first identity
Attaching a photo should be enough on its own - typing the roaster and bean
name becomes optional instead of required, and extraction fills them in
too, not just the surrounding details. This is a real architecture change,
not a small tweak, and needs restructuring when it's tackled:

- **The schema blocks this today.** `entries.bean_profile_id` is
  `NOT NULL` - every entry must be linked to a specific bean at creation
  time. Submitting with no typed name means either the FK becomes
  nullable (and something has to show in History while it's still
  unresolved), or the app creates a provisional bean profile immediately
  and merges/corrects it once extraction resolves a real name. Needs a
  real design decision, not just a code change.
- **The extraction prompt currently excludes identity on purpose** ("roaster
  and bean_name are NOT part of this extraction... always resolved
  synchronously, never waited on from a photo" - the original 0.2.0
  design). That constraint gets lifted here: the prompt needs to also
  attempt roaster + bean name from the photo.
- **Overlaps with 1.2.0 (fuzzy repurchase matching).** If extraction
  returns "Detour Coffee" and an existing bean profile says "Detour
  Coffee Roasters," this needs the same fuzzy-matching problem 1.2.0
  already plans to solve, just triggered from the extraction side instead
  of the autocomplete field. Worth building them together or at least
  coordinating rather than solving matching twice.
- Manual typing stays available regardless (still the only option for
  cafe cups with nothing printed to photograph, and always the fast path
  when someone already knows the name).

Manual test closes 0.5.x: attach a photo with no typed roaster/bean name,
confirm the entry saves instantly anyway, confirm the name shows up
correctly once extraction resolves it, confirm it correctly links to an
existing bean profile on a repeat instead of creating a duplicate.

---

## MAJOR 1 - Stable

### 1.0.0
Tagged once 0.5.x's manual test passes. Data integrity and background job
reliability were already verified in 0.1.0 and 0.2.0, so this cycle only
covers what genuinely needs the whole system or time to observe:
- `1.0.1` - real-world use: daily use for 1-2 weeks, real bags and cafe cups
- `1.0.2` - deployment resilience: container restart doesn't lose data,
  LAN-only exposure confirmed

Manual full-system test closes 1.0.x.

### 1.1.0 - Fixing wrong data
Extraction retry + a real edit/delete UI for saved entries and ratings.
High priority - first thing after stable, since "fast one-way log" from
0.1.0 means there's currently no way to correct a mistake. Also where
viewing every rating logged against an entry (not just the latest) belongs,
per earlier discussion.

- **View the uploaded photo(s) on Entry Detail.** The photo that was
  actually submitted for an entry should be viewable there, not just the
  fields extracted from it - useful for checking a field against the bag
  by eye when extraction looks off.
- **Show photos from other entries of the same bean, for comparison** (in
  case one photo is blurry/bad and a past one is clearer). This turned out
  not to need the fuzzy matching 1.2.0 is for - `entries.bean_profile_id`
  already groups entries by an exact (case-insensitive) match on
  roaster + bean name since 0.1.0, so "other entries with this
  bean_profile_id" is a plain join, available today.
- **Re-run AI extraction from Entry Detail.** A button that re-triggers
  `run_extraction` for an entry using its own saved photo(s) - covers
  cases where a prompt fix (like 0.2.1) or a retry might get a better
  result the second time. Available today using just that entry's photos.
  Extending it to also consider photos from *other* bean profiles the
  system suspects are the same bean (e.g. "Detour Coffee" vs. "Detour
  Coffee Roasters") depends on 1.2.0's fuzzy matching - not available
  until that exists.
- **Manual field correction UI.** Same screen, the actual edit form for
  bag-detail fields and ratings referenced at the top of this milestone -
  AI re-extraction and manual editing are two different ways to fix the
  same wrong data, both belong here.

### 1.2.0 - Fuzzy repurchase matching
The 0.1.0 autocomplete only does exact/prefix text matches. High priority.

### 1.3.0 - Data backup sinks
`LocalXlsxSink` (formatted XLSX with Raw Data + Summary sheets) and
`GithubSink` (push to a separate private repo via personal access token),
both using the `export_log` table already present in the schema since
0.1.0. Human-readable reports, not a re-import source (see 1.10.0).

### 1.4.0 - AI narrative insights
`InsightGenerator` interface, using the `insight_narratives` table already
present in the schema. Interprets numbers 0.4.0 already computed - never
calculates them itself.

### 1.5.0 - Richer browsing
History filter/sort controls, Insights attribute-switcher dropdown (beyond
the fixed `process` grouping from 0.4.0).

### 1.6.0 - Ollama provider
Low priority. `BeanExtractor` was designed swappable from 0.2.0 onward
specifically for this - a new `ollama_extractor.py` plus one factory
branch, no redesign needed. Test head-to-head against the 1.0 baseline
before relying on it.

### 1.7.0 - Settings UI
Low priority. Takes over `RECENT_WINDOW_MONTHS`/`RECENT_WINDOW_COUNT` from
env vars, using the `settings` table already present in the schema.

### 1.8.0 - Multi-user/auth
Low priority. Uses the `users` table and nullable `user_id` columns already
present in the schema since 0.1.0.

### 1.9.0 - Visual design pass
Lowest priority, deliberately last functional-adjacent item. Colors,
typography, layout polish - no workflow changes. Everything up to this
point ships with plain, functional default styling only. Includes the
front-screen/mobile polish originally scoped as 0.3.1, based on actual
day-to-day phone use against the real deployment.

### 1.10.0 - Data export/import
JSON round-trip backup, for restoring or moving to a new install - not
CSV/XLSX. An entry can have several ratings, and that one-to-many
relationship doesn't flatten into rows and columns without ambiguity -
JSON keeps the structure exact so a restore is reliable. CSV (MVP) and
XLSX (1.3.0) stay as human-readable reports for opening in a spreadsheet,
not as a re-import source.

---

## MAJOR 2 - Blank slate

Deliberately unplanned. General candidates so far, not pinned to any
specific sub-version:

- Self-hosted Unraid template: a small XML file in this repo, added to
  Unraid via "Template repositories" pointing at its raw GitHub URL. Gives
  a nicer pre-filled install form and fixes the missing WebUI quick-launch
  button (the manually-added container has no `<WebUI>` field for Unraid
  to build that button from; the template format has one). "Click Update"
  itself already works today for any container regardless of template -
  this only makes *installing* it nicer.
- Unraid Community Applications feed listing (public template submission)
- Proxmox VE Helper-Scripts install script (community submission)
- Web-lookup enrichment: describe a bean by text or photo, app searches
  the internet to fill in the gaps - explicitly the lowest priority idea
  on this whole list
- Human-readable photo filenames: currently `{entry_id}_{yyyymmdd}_{upload_order}.jpg`
  (e.g. `2_20260803_1.jpg`), meaningless without cross-referencing the
  database. Include the roaster/bean name or some other identifiable key
  so browsing the photos folder directly on disk is actually useful.

---

## MAJOR 3 - iOS offline-first companion app (concept)

Concept stage only, not scoped in detail - captured here because it's a
real architectural direction the app should grow toward, not a vague
someday-idea. The web app is LAN-only by design (see 0.3.0), which means
it's unreachable whenever the phone isn't on the home network. A native
iOS app would:

- Queue new entries/ratings locally when the server can't be reached, and
  sync them once it can (LAN-only, so "can't reach it" will be common -
  away from home, phone on cellular, etc).
- Cache Insights data for offline viewing.

Depends on 1.10.0 (JSON export/import) existing first as the natural
sync payload shape, and on the rest of MAJOR 1 being stable before taking
on a second client.

## MAJOR 4 - On-device AI/OCR (concept)

Concept stage only, depends on MAJOR 3 (the iOS app) existing first. Once
there's a native client, explore what bag/menu-photo extraction can happen
directly on the device (e.g. Apple's Vision/on-device model frameworks)
instead of round-tripping to Claude's API - most relevant for the
"phone can't currently reach the server or the internet" case that 3.0.0
is already solving for.
