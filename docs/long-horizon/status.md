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
- Public repository `574210187-ship-it/zhou-livecase-bot-kit` was created with public visibility and populated through commit `c85622c6ca2f6206e4a82439c12fb9482b55bb20`.
- Anonymous raw readback returned HTTP 200 for startup protocol, metadata, rule registry and release ZIP; ZIP CRC and declared SHA matched.

## Changed Files

- Provider adapter and gate code under `src/zhou_livecase/providers/`.
- External CLI `src/zhou_livecase/external_bot_entrypoint.py`.
- Public rule packs under `rules/public-v1.0/`.
- Grok/Muse manuals and failure playbook under `docs/`.
- 27 new/changed public files plus expanded regression tests.

## Failed Checks

- none

## Blockers

- Grok and Muse execution environments are outside this window. Their private table/COS authorizations and route canary receipts require the user to send the public startup instruction to each Bot.

## Next Action

- Publish the final anonymous examples/rebuilt ZIP revision, then give the user one Grok instruction and one Muse instruction with fixed public links.

## Last Updated

- 2026-11-06 Asia/Shanghai
