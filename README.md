# Coffee Bean Tracker

A self-hosted web app for logging and rating coffee, whether it's a bag you
bought or a one-off cup from a cafe. Photos of bag labels or menu boards get
read automatically in the background to fill in details like origin, process,
and roast level, so logging something takes seconds. Over time it builds up
data on what you actually like.

## AI disclosure

This project was built using Claude (Anthropic) as an AI coding assistant.
The author designed the data model, workflow, and feature scope; Claude wrote
most of the implementation.

## Status

Pre-release, actively being built. See the roadmap below for what's done and
what's next.

## Prerequisites

- Docker and Docker Compose installed on the host you're deploying to
- An Anthropic API key (only needed once photo extraction is enabled, from
  milestone 0.2.0 onward) from [console.anthropic.com](https://console.anthropic.com)

## Quick start

```
git clone https://github.com/help-for-me/Coffee-Bean-Tracker
cd Coffee-Bean-Tracker
cp .env.example .env
docker compose up -d
```

## Configuration

All settings are set via the `.env` file. Copy `.env.example` to `.env` and
adjust as needed.

| Variable | Description | Default |
|---|---|---|
| `EXTRACTOR_PROVIDER` | Which vision extractor fills in bag details from photos. `claude` for now; `ollama` arrives in milestone 1.3.0. | `claude` |
| `CLAUDE_MODEL` | Claude model used for photo extraction. | `claude-haiku-4-5-20251001` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Only used for photo extraction. | none |
| `APP_PORT` | Port the app listens on. | `8000` |
| `PHOTOS_PATH` | Where uploaded photos are stored, relative to the app's working directory (resolves correctly both locally and in Docker). | `data/photos` |
| `LOG_PATH` | Where application logs are written (rotates at 5MB, keeps 3 backups) - grab this file directly instead of digging through the Docker UI's Logs panel. | `data/logs/app.log` |
| `RECENT_WINDOW_MONTHS` | How many months count as "recent" for insights. | `4` |
| `RECENT_WINDOW_COUNT` | How many entries count as "recent" for insights. | `10` |

A few more variables (for the local XLSX and GitHub backup exports) are
reserved for milestone 1.1.0 and aren't used yet. They're listed, commented
out, in `.env.example`.

## Deployment note

This app is meant to run on your own network only. It never needs an open
inbound port; it only reaches out to Claude's API for photo extraction. Bind
its port to your LAN and don't forward it through your router or firewall.

## Roadmap

At-a-glance checklist below. See [ROADMAP.md](ROADMAP.md) for what each
milestone actually contains, deployment specifics, and manual test
criteria.

- [x] 0.1.0 - Foundation (schema, manual entry)
- [x] 0.2.0 - AI/OCR extraction loop
- [x] 0.2.1 - Extraction accuracy fix (process/region/variety confusion)
- [x] 0.3.0 - Deploy on the primary Docker host (Docker, GHCR)
- [x] 0.4.0 - Insights (stats and charts)
- [x] 0.5.0 - Photo-first identity
- [x] 0.6.0 - Exportable application logs
- [x] 0.7.0 - Fixing wrong data
- [x] 0.8.0 - Fuzzy repurchase matching
- [x] 0.9.0 - AI narrative insights
- [ ] 1.0.0 - Stable
- [ ] 1.1.0 - Data backup sinks
- [ ] 1.2.0 - Richer browsing (filters, attribute switcher)
- [ ] 1.3.0 - Ollama provider
- [ ] 1.4.0 - Settings UI
- [ ] 1.5.0 - Multi-user/auth
- [ ] 1.6.0 - Visual design pass
- [ ] 1.7.0 - Data export/import
- [ ] 2.0.0 - Blank slate
- [ ] 3.0.0 - iOS offline-first companion app (concept)
- [ ] 4.0.0 - On-device AI/OCR (concept)

## License

MIT, see [LICENSE](LICENSE).
