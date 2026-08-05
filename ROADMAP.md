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

**MAJOR 0 stays open past 1.0.0 existing.** 0.7.0-0.9.0 sit numerically
before 1.0.0 but don't wait on it or block it - 1.0.0 is a real-world
observation checkpoint (see below) that runs in parallel with, not ahead
of, continued feature work. "Stable" is a confidence checkpoint to tag
whenever it's earned, not a gate the rest of development sits behind.

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
  never co-ferment wording; tasting notes are flavour descriptors only,
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

### 0.3.0 - Deploy on the primary Docker host ✅ shipped 2026-08-04
Swapped ahead of Insights, and split from polish, so this one thing happened
first: something real running on real hardware, so every milestone after
this gets tested by clicking "Update" on the deployed container instead of
manually reinstalling dependencies on a laptop each time. Host specifics
(hostname, hardware) live in `private/deployment-notes.md` - gitignored,
never on GitHub.

- **Finished the Dockerfile.** Was backend-only (a deliberate stub from
  when the frontend didn't exist yet); now a real multi-stage build:
  compiles the React app (`npm run build`), serves the static files from
  the same FastAPI container as the API (`StaticFiles` mount, added after
  the API routers so specific routes still win).
- **GHCR publish pipeline** - built and working
  (`.github/workflows/docker-publish.yml`, fixed for lowercase image
  names). Publishes `ghcr.io/help-for-me/coffee-bean-tracker` on every push
  to `main` and on version tags.
- **Deployed.** Running on the primary Docker host (Iron, via Unraid)
  pointed at `ghcr.io/help-for-me/coffee-bean-tracker:latest`, using the
  volumes already defined in `docker-compose.yml` (`./data`, `./photos`,
  `./exports`).
- **LAN-only.** Port bound to the LAN, no port-forwarding - the app only
  ever calls out to Claude's API, never accepts inbound traffic from the
  internet.

Manual test (passed): confirmed actually running on the deployed
container and reachable on the LAN. Confirmed a container restart doesn't
lose data.

0.3.1 ("Deployment polish" - self-hosted Unraid template, front screen/mobile
polish) was retired as its own milestone: 0.3.0 is functional as-is, and
these were nice-to-haves, not blockers. Their two pieces moved to where they
naturally fit long-term - the Unraid template into "Future ideas" below, and
mobile/front-screen polish folded into 1.6.0, which already covers general
UI polish.

### 0.4.0 - Insights ✅ shipped 2026-08-04
Deterministic stats engine + fixed charts, built on real data from 0.1.0
(manual entry) and 0.2.0 (extraction). No AI-generated narrative summary
yet (that's 0.9.0) - just the charts and numbers.

- Rolling average score by month
- Favourite processes, origin countries, and tasting notes - "favourite"
  = highest average score, same computation as the original "by process"
  chart, extended to two more dimensions. Tasting notes are free text
  (comma- or dash-separated depending on the roaster, e.g. "Mango, Papaya"
  vs. "Hibiscus - Peach - Tropical Fruits") so they're tokenized into
  individual notes and deduped case-insensitively before ranking.
  Deliberately ignores co_ferment_status/ingredient for now, per request -
  that's its own future cross-reference, not folded in here.
- Most-repurchased/reordered bean profiles, and whether score trends up or
  down across repeat entries
- "Recent" window: compare last 4 months vs. last 10 entries, whichever has
  more rated entries (`RECENT_WINDOW_MONTHS` / `RECENT_WINDOW_COUNT` env
  vars, fixed until the 1.4.0 Settings UI). Only applies once there's at
  least 4 months of history *and* at least 10 entries - a "Recent"/"All
  time" toggle only appears once it does; before that, everything is
  all-time.

Real use case this serves: pull up Insights on your phone in a coffee shop
and cross-reference a bag's printed origin/process/notes against what's
scored well for you before. A fancier version - type or scan a specific
bag's attributes and get an actual predicted score - would need real
matching/weighting logic across multiple attributes at once; noted as a
future idea below rather than built now.

Backend: `backend/insights/stats.py` (pure, DB-backed functions, no
framework dependency) + `GET /insights`. Frontend: a generalized
hand-rolled inline-SVG bar chart (`RankedScoreChart`, reused for process/
origin/tasting-note) and a line chart for the monthly trend - no charting
library, consistent with staying dependency-light and with "plain,
functional styling until 1.6.0." Verified in a real browser against
seeded data (multiple processes, origins, tasting notes including a
dash-delimited bag, multiple months, a repurchased bean) - no console
errors, both toggle states checked.

Manual test (passed): confirmed accurate against real entries.

### 0.5.0 - Photo-first identity ✅ shipped 2026-08-04
Attaching a photo should be enough on its own - typing the roaster and bean
name becomes optional instead of required, and extraction fills them in
too, not just the surrounding details. This is a real architecture change,
not a small tweak:

- **Design decision:** `entries.bean_profile_id` stays `NOT NULL`. A
  provisional bean profile (roaster "Unidentified", bean_name = its own
  row id, e.g. "#12") gets created immediately when someone saves a photo
  with no typed name; once extraction resolves a real roaster/bean name,
  that same row gets renamed in place, or - if the resolved name matches
  an existing profile (a repeat purchase) - every entry on the
  placeholder gets re-linked to the existing profile and the placeholder
  is discarded. Chosen over making the FK nullable specifically to avoid
  touching every existing join in `crud.py` that assumes a profile is
  always present. Migration: `bean_profiles.is_provisional`
  (`SCHEMA_VERSION` 2), additive only.
- **The extraction prompt now attempts roaster + bean name too** - lifting
  the original 0.2.0 constraint that excluded identity entirely. Always
  attempted, even for entries that already have a typed name; the backend
  only ever acts on it when the entry's profile is still provisional, so
  a typed name is never overwritten.
- **Validation:** identity (typed, or via a bag + photo) is required at
  the router - cafe cups always need it typed (nothing printed to
  photograph for identity), matching the New Entry form's client-side
  check.
- **Still open, deferred to 0.8.0 (fuzzy repurchase matching):** identity
  resolution reuses the existing exact/case-insensitive match - if
  extraction returns "Detour Coffee" and an existing profile says "Detour
  Coffee Roasters," today that creates a second profile rather than
  merging. Real fuzzy matching arrives with 0.8.0, shared with the manual
  autocomplete's version of the same problem.
- Manual typing stays available regardless (still the only option for
  cafe cups, and always the fast path when someone already knows the
  name).

Built, pytest-covered (15 new cases: provisional creation, in-place
rename, merge-into-existing, never overwriting a typed identity, router
validation for all three entry-type/photo/identity combinations), and
verified in a real browser (History and Entry Detail correctly
distinguish resolved / still-identifying / failed-to-identify states, New
Entry's validation and hint text match the backend rule).

**0.5.1 - real-world manual test ✅ passed 2026-08-04.** Tested on an
actual phone with a real bag (Monogram): entry saved instantly with no
typed roaster/bean name, and the name showed up correctly once extraction
resolved it ("Monogram Coffee — Jairo Aroila"). The third check - links
to an existing profile on a repeat instead of creating a duplicate -
confirmed the known gap already noted above: this bag had been logged
before under slightly different text ("Monogram" / "Jario Arcila"), and
since identity resolution is exact-text match only until 0.8.0, it
created a second profile rather than merging. Expected, not a new defect
- accepted as a pass since 0.5.0 never claimed to solve fuzzy matching,
just photo-first identity.

### 0.6.0 - Exportable application logs ✅ shipped 2026-08-04
**High priority**, prompted by the 0.5.1 test attempt: extraction failed
and the only way to diagnose it was a screenshot conversation, not an
actual error. A real, buildable capability (not an observation period),
so it gets its own MAJOR-0 minor version rather than sitting as a
sub-item under 1.0.0's tagging cycle.

Write logs to a file under the already-mounted `data/` volume (not just
Docker's ephemeral log buffer), so they survive restarts and are
grabbable directly from Unraid's file browser - the same access pattern
already used for the SQLite DB and photos - without going through the
Docker UI's Logs panel each time.

### 0.7.0 - Fixing wrong data ✅ shipped 2026-08-04
Extraction retry + a real edit/delete UI for saved entries and ratings.
High priority - since "fast one-way log" from 0.1.0 means there's
currently no way to correct a mistake, this comes right after 0.6.0's
logging infra rather than waiting on 1.0.0's real-world-use observation
period to finish first (that period runs in parallel, not ahead of this).
Also where viewing every rating logged against an entry (not just the
latest) belongs, per earlier discussion.

- **View the uploaded photo(s) on Entry Detail.** The photo that was
  actually submitted for an entry should be viewable there, not just the
  fields extracted from it - useful for checking a field against the bag
  by eye when extraction looks off.
- **Show photos from other entries of the same bean, for comparison** (in
  case one photo is blurry/bad and a past one is clearer). This turned out
  not to need the fuzzy matching 0.8.0 is for - `entries.bean_profile_id`
  already groups entries by an exact (case-insensitive) match on
  roaster + bean name since 0.1.0, so "other entries with this
  bean_profile_id" is a plain join, available today.
- **Re-run AI extraction from Entry Detail.** A button that re-triggers
  `run_extraction` for an entry using its own saved photo(s) - covers
  cases where a prompt fix (like 0.2.1) or a retry might get a better
  result the second time. Available today using just that entry's photos.
  Extending it to also consider photos from *other* bean profiles the
  system suspects are the same bean (e.g. "Detour Coffee" vs. "Detour
  Coffee Roasters") depends on 0.8.0's fuzzy matching - not available
  until that exists.
- **Manual field correction UI.** Same screen, the actual edit form for
  bag-detail fields and ratings referenced at the top of this milestone -
  AI re-extraction and manual editing are two different ways to fix the
  same wrong data, both belong here.

**Known extraction accuracy issue, fixed here** (see CLAUDE.md's
"Extraction prompt changes" policy):
- Bilingual packaging text (e.g. "Whole Bean Coffee / Grains de café" on
  a Canadian bag) leaking into `printed_tasting_notes` instead of being
  recognized as a product-type label and excluded. The extraction prompt
  now explicitly calls this out as text to exclude from that field.

Built: `GET /photos/{id}` (DB-trusted path lookup, no path-traversal
surface since the path is never client-supplied), own + related photo
galleries on Entry Detail, `POST /entries/{id}/reextract` (re-runs
extraction against the entry's own saved photos in the background),
`PATCH`/`DELETE /entries/{id}` and `PATCH`/`DELETE
/entries/{id}/ratings/{rating_id}` (whitelisted, `exclude_unset`-based
partial updates so an explicit null correctly clears a field), with
entry deletion cascading ratings/photos/farms rows in one transaction and
removing photo files from disk. Pytest-covered (36 new cases across crud
and router level, full suite now 150 passing) and verified end-to-end in
a real browser: viewed both photo galleries, edited bag details and a
rating, deleted a rating, re-ran extraction, and deleted an entire entry -
confirming its photo file was actually removed from disk, not just its
DB row.

### 0.8.0 - Fuzzy repurchase matching ✅ shipped 2026-08-04
The 0.1.0 autocomplete only does exact/prefix text matches. High priority.

Built on stdlib `difflib` (no new dependency) - reuses the same
`SequenceMatcher.ratio()` approach `claude_extractor.py` already uses for
vocab correction:
- **Autocomplete suggestions** (`search_bean_profiles`) fall back to a
  fuzzy-ranked match (cutoff 0.6) to fill any suggestion slots the
  prefix-only `LIKE` match leaves empty - catches typos like "Detuor" for
  "Detour". Zero merge risk, since the user still picks explicitly from
  the list.
- **Extraction-resolved identity** (`resolve_provisional_profile`) falls
  back to a conservative fuzzy match (cutoff 0.85) before creating a new
  profile - catches OCR typos like the real 0.5.1 case ("Jairo Aroila" vs
  "Jario Arcila"), the same bag read slightly differently across two
  photo submissions. Typed-entry identity (`resolve_bean_profile`) stays
  exact-match only, since autocomplete is already the safety net there
  and a typed identity is a deliberate action, not an OCR guess.

Pytest-covered (5 new cases, including a same-roaster/different-bean case
that must NOT auto-merge, to guard against false positives) and verified
in a real browser - typing a transposed-letter typo ("Detuor Coffee
Roasters") correctly surfaced the existing "Detour Coffee Roasters"
profile in New Entry's autocomplete.

### 0.9.0 - AI narrative insights ✅ shipped 2026-08-04
`InsightGenerator` interface, using the `insight_narratives` table already
present in the schema. Interprets numbers 0.4.0 (and 1.2.0's statistical
rigor, once that exists) already computed - never calculates them itself.

- **Flavour/preference recommendations**, explicitly requested: not just
  narrating "your scores trended up in July" but something closer to "you
  consistently rate Honey-process Colombian coffees with stone fruit notes
  highest - look for those" - a genuine recommendation, not just a
  summary. This is squarely what this milestone is for; the 0.4.0/1.2.0
  breakdowns are the numbers it interprets, never the other way around.

Built: `InsightGenerator` abstract base (`backend/insights/base.py`,
mirrors `BeanExtractor`'s shape) with a `ClaudeInsightGenerator`
implementation and a `get_generator()` factory (`NARRATIVE_PROVIDER` env
var, "ollama" reserved for 1.3.0 same as extraction). The prompt
explicitly requires a recommendation grounded in the highest-scoring
pattern(s) actually present in the data, not a plain recap. Synchronous
"Generate summary" button on the Insights page (`POST
/insights/narrative?window=`) - no background-job plumbing needed, unlike
photo extraction, since there's no upload request it would otherwise
block; results cache per time-window in `insight_narratives` and
`GET /insights/narrative?window=` returns the latest cached summary.
Pytest-covered (14 new cases: crud caching, a fake-generator unit test
confirming only the window-scoped stats ever reach the prompt, and
router-level success/no-API-key-failure cases) and verified in a real
browser, including the missing-API-key error path (dev has no key,
matching extraction's established behaviour) and, via a mocked network
response, the successful-generation rendering path.

---

## MAJOR 1 - Stable

### 1.0.0
Tagged once 0.5.x's manual test passes. Data integrity and background job
reliability were already verified in 0.1.0 and 0.2.0, so this cycle only
covers what genuinely needs the whole system or time to observe. Runs in
parallel with 0.7.0-0.9.0's continued feature work, not ahead of it - see
the versioning policy note above.

**`1.0.1` - real-world use (1-2 weeks, spread across real days - not
batch-logged in one sitting, the point is ordinary daily use):**
- [ ] At least ~10 real entries logged over the period
- [ ] At least one bag entry via photo (no typed name) and at least one
  via manual typing
- [ ] At least one cafe cup entry
- [ ] At least one repeat: re-rate a bean you've already logged before
  (exercises the "rate a previous bean" flow and, incidentally, whatever
  bean-profile linking behaviour it hits)
- [ ] Note anything that felt slow, confusing, or wrong as it happens -
  a screenshot and a sentence is enough, doesn't need to be formal

**Report back:** export `data/logs/app.log` after the 1-2 weeks and send
it over - every entry (type, typed vs. photo identity, score) and every
rating is logged as it happens, so the first three boxes above can be
confirmed directly from the file instead of tracked by hand. Any request
slower than 3 seconds is flagged in there too. The fourth box (anything
that felt confusing or wrong) is the one thing logs can't capture on
their own - a quick note when it happens is still the way to report that
one.

**`1.0.2` - deployment resilience:**
- [ ] Restart the container on Iron (Unraid's stop/start, not a fresh
  reinstall) and confirm every entry, rating, and photo is still there
  afterward
- [ ] Confirm the app is unreachable from outside the LAN - easiest
  check: turn off WiFi on your phone (cellular only) and confirm the
  app's URL fails to load
- [ ] Confirm there's no port-forwarding rule for this app's port on your
  router (quick look in the router's admin panel)

**Report back:** pass/fail on each of the three boxes above. The first
box can be confirmed from the same log export - every startup logs the
current entry/rating/photo counts, so a restart's before-and-after
numbers are directly comparable in the file. The other two are physical/
network checks with no log-based substitute. A fail on the LAN-exposure
checks is treated as urgent, not routine - it means the app is reachable
from the internet, which the project's design explicitly assumes never
happens.

Manual full-system test closes 1.0.x once both `1.0.1` and `1.0.2` report back clean.

### 1.1.0 - Data backup sinks
Gives the Export tab (scaffolded since 0.1.0, empty ever since - flagged
as an unscheduled gap and given a real home here) an actual implementation:

- **CSV export** - the simplest sink, no external dependency, built first.
- `LocalXlsxSink` (formatted XLSX with Raw Data + Summary sheets)
- `GithubSink` (push to a separate private repo via personal access token)

All three use the `export_log` table already present in the schema since
0.1.0. Human-readable reports, not a re-import source (see 1.7.0).

### 1.2.0 - Richer browsing
History filter/sort controls, Insights attribute-switcher dropdown (beyond
the fixed `process`/origin/tasting-note grouping from 0.4.0) - including
`brew_style` (Pour Over/Espresso/French Press/Cafe-made/Other, already on
`ratings` since 0.1.0, unused for insights until now) as a switchable
dimension.

- **Brew-method-sliced insights**, requested alongside the switcher: not
  just "favourite tasting notes" but "favourite tasting notes *when
  brewed as Espresso*" - the same bean can taste different depending on
  brew method, so this is a real cross-tab (brew method x tasting
  note/origin/process), not just one more flat ranked dimension like
  0.4.0's breakdowns. Worth designing together with the attribute
  switcher rather than bolting on separately.
- **Statistical rigor for the "favourite X" rankings**, flagged as a real
  gap in 0.4.0's output: a single average score with no sense of spread
  or sample size is misleading once real data has outliers - e.g. a
  tasting note that appears once at a 9 currently outranks one that
  appears ten times averaging 8.5. Options to weigh here: showing a
  min-max range or standard deviation alongside the average (cheapest,
  most honest - let the reader judge confidence themselves), or ranking
  by a lower-confidence-bound score (e.g. mean minus one standard error,
  or a proper Wilson/Bayesian-average style adjustment) so thin-sample
  outliers don't visually dominate the top of the chart. Needs a real
  decision, not just "add error bars" - the two approaches produce
  different rankings, not just different visuals.

### 1.3.0 - Ollama provider
Low priority. `BeanExtractor` was designed swappable from 0.2.0 onward
specifically for this - a new `ollama_extractor.py` plus one factory
branch, no redesign needed. Test head-to-head against the 1.0 baseline
before relying on it.

**Not drafted ahead of schedule** (2026-08-05): needs the user's own
Ollama endpoint/infrastructure decision first (self-host where, which
model) and can't be meaningfully validated without a live Ollama server
to run the head-to-head test this section itself calls for.

### 1.4.0 - Settings UI
Low priority. Takes over `RECENT_WINDOW_MONTHS`/`RECENT_WINDOW_COUNT` from
env vars, using the `settings` table already present in the schema.

- **Plain-language prompt editing.** A section for adjusting the
  extraction prompt (`claude_extractor.py`) and the narrative insight
  prompt (`claude_generator.py`) without touching code - type an
  instruction in plain English (e.g. "always exclude bilingual packaging
  text" or "keep the insight summary to one sentence") and it's folded
  into the underlying prompt template. Replaces having to wait on a code
  change (like 0.7.0's known-issues list, or the post-launch narrative-
  length fix) for this kind of adjustment.

### 1.5.0 - Multi-user/auth
Low priority. Uses the `users` table and nullable `user_id` columns already
present in the schema since 0.1.0. There's no login of any kind before
this milestone - every endpoint is reachable by anyone who can reach the
instance, which is the accepted tradeoff for a single-user self-hosted
app until this lands. Scope CORS (currently `allow_origins=["*"]`,
appropriate only while there's no login to protect) down to the app's own
origin(s) as part of the same change.

Also worth revisiting then: running the Docker container as a non-root
user. Deferred for now since `data/` is a bind-mounted volume on Iron and
changing the container's user without first confirming what owns that
folder on the host risks breaking write access to the database on the
next deploy.

**Not drafted ahead of schedule** (2026-08-05): security-sensitive and
architecturally significant - needs a decision on the auth mechanism
itself (a single shared password vs. real per-user accounts, session vs.
token) before building, the same way 0.5.0's provisional-profile design
was confirmed with the user before being built, not guessed at.

### 1.6.0 - Visual design pass
Lowest priority, deliberately last functional-adjacent item. Colours,
typography, layout polish - no workflow changes. Everything up to this
point ships with plain, functional default styling only. Includes the
front-screen/mobile polish originally scoped as 0.3.1, based on actual
day-to-day phone use against the real deployment.

**Not drafted ahead of schedule** (2026-08-05): purely aesthetic and
personal (colours, typography, style direction) - there's no objectively
correct implementation to build ahead of the user's own taste.

### 1.7.0 - Data export/import
JSON round-trip backup, for restoring or moving to a new install - not
CSV/XLSX. An entry can have several ratings, and that one-to-many
relationship doesn't flatten into rows and columns without ambiguity -
JSON keeps the structure exact so a restore is reliable. CSV (MVP) and
XLSX (1.1.0) stay as human-readable reports for opening in a spreadsheet,
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
- Predicted match score for a specific candidate bag: type in (or photo-
  extract) a bag's origin/process/tasting notes while standing in a shop,
  and get a single predicted score from combining historical averages
  across all three - real matching/weighting logic across multiple
  attributes at once, a step up from the 0.4.0 Insights breakdowns (which
  only rank one attribute at a time).
- A "co-fermented vs. not" cross-reference in Insights, alongside the
  0.4.0 favourite-process breakdown (deliberately excluded from 0.4.0's
  process ranking, per request, so it doesn't muddy plain process
  preference).
- Language/locale selector in the Settings UI (1.4.0): per-user choice
  between the major English variants - at least US English, UK English,
  and Canadian English (today's fixed default - see CLAUDE.md). Affects
  UI text and the wording instruction sent to the AI for generated
  content (e.g. the Insights summary), not extracted bag text, which is
  always copied verbatim from the label regardless of this setting.

---

## AI-suggested features

Ideas Claude has floated unprompted, not requested by the user. **None of
these get built without explicit agreement first** - this list exists so a
good idea doesn't get lost, not as an approved backlog. Move an item out of
this section (into a real MINOR/MAJOR slot, or MAJOR 2's candidate list)
once it's actually been agreed to; drop it entirely if it turns out not to
be wanted.

- **Freshness flag on entries.** `roast_date` is already captured for most
  bags - flag or visually mark entries past a typical peak-freshness
  window (roughly 2-8 weeks post-roast depending on process) on History/
  Entry Detail, so a stale bag doesn't get blamed on the bean itself.
- **Cost-per-cup / value ranking.** `price_paid` and `bag_weight_g` are
  already captured - a "best value" ranking (score relative to $/100g or
  estimated $/cup) alongside the existing "best score" rankings in
  Insights, for the days budget matters as much as flavour.
- **Roaster-level leaderboard.** Every existing Insights ranking groups by
  bean; grouping by roaster instead (average across everything from a
  given roaster) answers a different, also-useful question - "which
  roasters do I trust," not just "which specific bag."
- **Proactive repeat-purchase surfacing.** 0.8.0's fuzzy matching already
  merges a re-typed identity into the right profile after the fact - this
  would surface it *before* saving ("You've had this before, rated it
  8.5 on 2026-06-01") right in the New Entry form, using the same fuzzy
  match while typing rather than only on submit.
- **Tasting-note trends over time.** The favourite-notes ranking (0.4.0)
  is a snapshot; a month-by-month view of which notes show up and how
  they score would show a palate shifting over time, not just where it
  currently stands.
- **Origin map view.** A simple world map shading the countries logged so
  far (by count or average score) - Insights' rankings are all lists;
  this would be the one visual/spatial view.
- **"Try something new" nudge.** If recent entries cluster heavily on 1-2
  roasters, a gentle suggestion to branch out - low-effort, ties into
  MAJOR 2's already-listed web-lookup enrichment idea if that ever lands.

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

Depends on 1.7.0 (JSON export/import) existing first as the natural
sync payload shape, and on the rest of MAJOR 1 being stable before taking
on a second client.

## MAJOR 4 - On-device AI/OCR (concept)

Concept stage only, depends on MAJOR 3 (the iOS app) existing first. Once
there's a native client, explore what bag/menu-photo extraction can happen
directly on the device (e.g. Apple's Vision/on-device model frameworks)
instead of round-tripping to Claude's API - most relevant for the
"phone can't currently reach the server or the internet" case that 3.0.0
is already solving for.
