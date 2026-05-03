# ADR-075 — CI matrix expands to Ubuntu alongside macOS

> Status · Accepted (amends ADR-040)
> Date · 2026-05-02
> TA anchor · /stack
> Related ADR · ADR-040 (amended; not superseded)

## Context

ADR-040 (2026-04-27) constrained CI to macOS-only at v1, citing two
reasons: (a) macOS Apple Silicon is the primary supported configuration,
and (b) Linux darktable behavior is a separate validation surface that
CI passing wouldn't actually validate.

Eight months later both reasons hold partially but the trade-off has
shifted:

- **The CI tier doesn't invoke darktable.** Unit + integration tests
  use stubs / mocks for any subprocess that would call darktable-cli.
  E2E tests (which DO invoke darktable) run pre-release via
  `scripts/pre-release-check.sh`, never in CI. So "Linux CI doesn't
  prove darktable works on Linux" is correct but irrelevant — CI on
  Linux validates the Python code paths, not darktable.
- **Distribution intent grew.** PyPI is still deferred (the user's
  v1.4.0 statement), but `pip install chemigram` from GitHub already
  works for non-mac users, and several Python-only consumers
  (vocabulary scripts, eval scripts, the CLI's read-only surface)
  don't need darktable at all.
- **Linux runners are cheaper and faster on GitHub Actions.** The
  cost argument from ADR-040 was about adding Linux to a small matrix;
  in practice it's a small percentage of total CI time.

## Decision

Add `ubuntu-latest` to the OS matrix in `.github/workflows/ci.yml`,
alongside `macos-latest`. Keep the Python 3.11/3.12/3.13 matrix.
Total job count: 6 (2 OS × 3 Python).

CI steps remain unchanged — they don't invoke darktable, so they run
identically on both OSes. E2E tests stay out of CI per ADR-040.

ADR-040 is **amended, not superseded**: its core decisions (GitHub
Actions, Python matrix, no E2E in CI, dev extras everywhere) remain.
This ADR refines only the OS dimension.

## Rationale

- **CI now validates Python-side correctness across both OSes** the
  project most plausibly runs on. macOS stays primary; Linux gains
  parity.
- **No darktable required.** The chain `unit → integration → manifest
  audit (B6) → cli-reference sync` only touches Python code + on-disk
  fixtures. Linux runners handle this fine.
- **Distribution-friendly.** A green Linux CI badge tells potential
  contributors / users that the Python codebase isn't macOS-only.

## Alternatives considered

- **Linux + macOS + Windows:** Windows not a target. Deferred.
- **Linux for one Python version, macOS for all three:** asymmetric;
  saves marginal CI time at the cost of clarity. Easier to read with
  full parity.
- **Move E2E into CI on Linux via Docker with darktable:** out of
  scope for this ADR; the per-OS darktable-behavior divergence remains
  a real concern that ADR-040 already addressed.

## Consequences

Positive:
- Faster initial CI feedback (Linux runners are typically faster than
  macOS runners on GitHub Actions free tier).
- Catches Linux-specific Python bugs (path separators, line endings,
  shell escape behavior) before they reach a real Linux user.
- Matches the v1.4.0 "infra cleanup" framing — CI is no longer a
  visible asymmetry against contributing.

Negative:
- 2× the CI minutes per push. For a public repo this is free; for a
  private one it's still small.
- A Linux-only CI failure could surface that doesn't reproduce on
  macOS. That's the whole point — but it can be a friction point if a
  contributor's local box is macOS-only.

## Implementation notes

- `.github/workflows/ci.yml` — `runs-on: ${{ matrix.os }}` with
  `os: [macos-latest, ubuntu-latest]`.
- ADR-040's "macOS-only" line is now historical; this ADR documents
  the amendment. The original ADR stays unedited per the append-only
  rule.
- `docs/testing.md` (if it diverges from this) gets a one-line update
  to point at ADR-075.
