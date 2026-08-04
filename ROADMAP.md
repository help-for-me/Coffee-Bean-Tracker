# Roadmap

Detailed planning for each milestone. For an at-a-glance checklist, see the
[README](README.md#roadmap).

## Versioning policy

Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **MAJOR** - a fundamentally new phase (0 = building the MVP, 1 = stable, 2 = blank slate)
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

### 0.2.0 - AI/OCR extraction loop (built, manual test in progress)
Photo upload, `ClaudeExtractor`, background-task wiring, `extraction_status`
lifecycle - fills in bag-printed attributes (origin, process, roast level,
tasting notes, co-ferment) automatically and correctly files them into the
entry.

Manual test (in progress): submit a bag photo, confirm it saves instantly,
confirm the background job correctly fills in and files the details,
confirm a bad photo fails gracefully. Also confirm background job
reliability: a blurry photo, a photo with no visible text, no internet, a
bad API key - `extraction_status` must always resolve (`complete` or
`failed`, never stuck `pending`), app must never crash.

Already verified (no real API key needed for this part): instant save,
graceful failure with a missing/bad key, no crash, no console errors -
covered by 36 automated pytest cases plus a live browser check. What's
left: confirming *accuracy* against a real photo with a real key - that
part only the repo owner can judge.

Patches: none yet. Will be added here if the manual test above turns up
anything needing a fix before 0.3.0 starts.

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

### 0.3.1 - Deployment polish
Everything else that makes the deployment nicer to live with, once the
core of 0.3.0 is already working:

- **Self-hosted Unraid template** (not the public CA feed - see the
  README's "Future ideas" for that). A small XML file in this repo, added
  to Unraid via "Template repositories" pointing at its raw GitHub URL.
  Gives a nicer pre-filled install form, privately, no review process.
  "Click Update" itself already works as of 0.3.0, for any container
  regardless of template - this just makes *installing* it nicer.
- **Front screen polish, mobile use** - a general UI pass once it's
  actually being used on a phone against the real deployment, not a dev
  server.

Manual test closes 0.3.1: using it for real, day to day, from a phone,
against the deployed container. LAN-only exposure gets confirmed, not
just assumed.

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

---

## MAJOR 1 - Stable

### 1.0.0
Tagged once 0.4.x's manual test passes. Data integrity and background job
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
point ships with plain, functional default styling only.

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

- Unraid Community Applications feed listing (public template submission)
- Proxmox VE Helper-Scripts install script (community submission)
- Web-lookup enrichment: describe a bean by text or photo, app searches
  the internet to fill in the gaps - explicitly the lowest priority idea
  on this whole list
