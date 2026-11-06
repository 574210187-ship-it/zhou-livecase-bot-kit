# Status

## Current Milestone

- Milestone 4 — Public release and GitHub readback (`active`)

## Escalation Level

- none

## Current Slice

- Publish the scanned v0.6.0 source and release ZIP to a new public repository, then read them back.

## Latest Evidence

- v0.6.0 implements capability preflight, route selection, human-readable payload validation, delegated-chat cleanup validation and route comparison.
- Sanitized transcript/deep rule packs were rebuilt; old private rule ZIPs were rejected because they contained real target IDs and host paths.
- 50/50 offline tests pass; release scan reports zero violations; release ZIP CRC passes.
- Release ZIP SHA256: `0cdd1977109540e6155e618d4d6a3808b1e1708c9d90ad150ae6d7584dc7794f`.

## Changed Files

- Provider adapter and gate code under `src/zhou_livecase/providers/`.
- External CLI `src/zhou_livecase/external_bot_entrypoint.py`.
- Public rule packs under `rules/public-v1.0/`.
- Grok/Muse manuals and failure playbook under `docs/`.
- 27 new/changed public files plus expanded regression tests.

## Failed Checks

- none

## Blockers

- None for local build. A new public GitHub repository still has to be created and populated before Milestone 4 can close.

## Next Action

- Create `574210187-ship-it/zhou-livecase-bot-kit` as a clean public repository, upload the scanned tree and ZIP, then verify anonymous metadata/file reads.

## Last Updated

- 2026-11-06 Asia/Shanghai
