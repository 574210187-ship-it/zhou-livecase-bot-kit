# Execution Plan

## State Machine

- Allowed states: `pending`, `active`, `blocked`, `done`
- Exactly one milestone is `active`.

## Milestone 1 — Public contract and capability router

- State: done
- Goal: add external Bot profiles, A/B capability preflight, authorization output and unified analysis envelope.
- Exit criteria: deterministic CLI and tests cover executable/missing-capability branches for Grok and Muse.
- Dependencies: existing v0.5.0 contracts.
- Verification: unit tests plus sample profile CLI runs.

## Milestone 2 — Human-readable content and delegated-chat gates

- State: done
- Goal: block prior low-quality table failures and require complete delegated-chat lifecycle evidence.
- Exit criteria: regression fixtures cover internal codes, placeholders, unsupported facts, wrong source identity, incomplete Q50, missing chat cleanup.
- Dependencies: Milestone 1.
- Verification: unit tests and adversarial fixture suite.

## Milestone 3 — Bot manuals and two-path experiment

- State: done
- Goal: write executable Grok/Muse startup instructions, A/B runbooks, metrics and route-selection report contract.
- Exit criteria: one command leads to preflight, authorized execution or exact block; both paths have comparable metrics and stop conditions.
- Dependencies: Milestones 1–2.
- Verification: dry-run/simulation with anonymous fixtures.

## Milestone 4 — Public release and GitHub readback

- State: active
- Goal: build scanned ZIP, publish public repository, pin commit/tag and verify download contents.
- Exit criteria: GitHub visibility public, fixed commit/tag, release ZIP SHA/CRC, repository and release download readback.
- Dependencies: Milestones 1–3.
- Verification: local tests, release scan/build, GitHub API/web readback.

## Milestone 5 — External Bot canary

- State: pending
- Goal: give Grok and Muse the same startup command; each runs A and B capability tests without production writes, then selects the faster valid route.
- Exit criteria: both return preflight, path metrics, zero-write test receipt and exact missing authorization list; production remains blocked until user grants table/COS access.
- Dependencies: Milestone 4 and user-side Bot access.
- Verification: external execution receipts and independent readback.
