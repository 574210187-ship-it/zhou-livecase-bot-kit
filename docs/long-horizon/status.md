# Status

## Current Milestone

- Milestone 5 — External Bot canary (`active`)

## Escalation Level

- none

## Current Slice

- Hand the same fixed public startup protocol to Grok and Muse; each must test both routes and return zero-write/canary evidence.

## Latest Evidence

- v0.6.0 implements capability preflight, route selection, human-readable payload validation, delegated-chat cleanup validation and route comparison.
- Sanitized transcript/deep rule packs were rebuilt; old private rule ZIPs were rejected because they contained real target IDs and host paths.
- Public repository `574210187-ship-it/zhou-livecase-bot-kit` was created with public visibility; the immutable `release-v0.6.0` branch is the canonical external-Bot entry.
- Anonymous raw readback returned HTTP 200 for startup protocol, metadata, rule registry and release ZIP; ZIP CRC, member count and declared SHA matched.

## Changed Files

- Provider adapter and gate code under `src/zhou_livecase/providers/`.
- External CLI `src/zhou_livecase/external_bot_entrypoint.py`.
- Public rule packs under `rules/public-v1.0/`.
- Grok/Muse manuals and failure playbook under `docs/`.
- Anonymous executable examples, fixed release links and 52 regression tests are included in the public package.

## Failed Checks

- none

## Blockers

- Grok and Muse execution environments are outside this window. Their private table/COS authorizations and route canary receipts require the user to send the public startup instruction to each Bot.

## Next Action

- User sends the fixed startup instruction to Grok and Muse; each returns preflight and equivalent A/B zero-write canary evidence before either receives private production authorization.

## Last Updated

- 2026-11-06 Asia/Shanghai
