# Changelog

All notable changes to this project are documented here.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
