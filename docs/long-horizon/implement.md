# Implementation Rules

## Work Batch Size

- One active milestone, one contract slice, then tests.
- Public examples use synthetic IDs and text only.

## Verification

- Narrow: `PYTHONPATH=src python3 -m unittest <test module>`.
- Full: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'`.
- Release: `python3 release/verify_release.py --root .` and `python3 release/build_release.py --output ...`.
- Public: GitHub repository visibility, fixed commit and downloaded ZIP SHA/CRC readback.

## Failure Policy

- Any missing capability/authorization is a structured block, never a guessed fallback.
- Same failure twice escalates to milestone diagnosis; do not stack more prompts.
- External Bot cannot write until capability profile, source snapshot, analysis gate and private adapter readiness all pass.
- B path cannot complete until every created ChatGPT conversation has a deletion receipt and refresh-after-delete absence proof.

## Data Safety

- No real token, secret, table ID, bucket, source transcript or runtime receipt enters Git/public ZIP.
- Public examples use placeholders and anonymous fixtures.
- Production credentials stay in the user's private execution environment and are requested by capability name only.

## Definition Of Done

- Code and docs alone are not production validation.
- Public release is done only after GitHub readback.
- External Bot production is done only after target-system four-way readback and independent auditor.
