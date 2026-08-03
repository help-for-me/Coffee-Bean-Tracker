# Changelog

All notable changes to this project are documented here.

Format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
