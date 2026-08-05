# Working on this project

## Anthropic API key expiry

The Anthropic API key configured on the Unraid deployment was set on
2026-08-04 and expires 30 days later (~2026-09-03). If any Unraid/deployment
work happens on or after 2026-08-29 (25+ days out), remind the user to
update the key before it expires.

## Roadmap

Read [ROADMAP.md](ROADMAP.md) for detailed milestone planning (what each
milestone contains, deployment specifics, manual test criteria) before
starting work on the next milestone. README.md has only the short
checklist version.

## Extraction prompt changes

Extraction accuracy issues found while testing 0.x (MVP) milestones get
logged in ROADMAP.md, not fixed immediately - the 0.2.1 patch (fixed
process/region/variety confusion right away) was the exception while
extraction accuracy was still actively being stabilized, not the standing
policy. From here on, prompt changes get consolidated into a single pass
during 0.7.0 - Fixing wrong data (see the known-issues list there in
ROADMAP.md) instead of being made piecemeal every time a new bag turns up
a small confusion.

## No emojis

Never use emojis anywhere in this project - UI text, code, commit messages,
comments, docs - unless the user explicitly asks for one in that specific
instance. This applies everywhere, not just the written docs (README/
CHANGELOG/commits) already covered by the project instructions' writing
style section.

## Canadian English

Everything in this project is written in Canadian English: UI text, docs,
commit messages, comments, and prompts sent to the AI (so its generated
narrative text - e.g. the Insights summary - comes back in Canadian
English too). In practice this means the British "-our"/"-re" spellings
(flavour, favourite, colour, behaviour, centre) rather than the American
ones, while still keeping the "-ize" endings (organize, recognize) and
other forms Canadian English shares with American - it's not a wholesale
switch to British English. `backend/tests/test_canadian_spelling.py`
guards docs and backend prose against the specific American-only forms
this project has hit before; extending the blocked-word list there is
fine if a new one turns up. One deliberate exception: the MIT `LICENSE`
file and its "License" heading in README.md stay as-is - that's a fixed
legal/GitHub convention, not prose. A per-user language selector (US/UK/
Canadian English) is on the roadmap at 2.X - see ROADMAP.md - not a
reason to hold off on Canadian English as the default now.
