"""Integration test: full versioning workflow against the Phase 0 v3 XMP.

Loads the real fixture, runs through snapshot → branch → checkout →
modify-via-synthesize → snapshot → diff → tag, and verifies each
expected state. No darktable invocation; pure XMP-level operations.
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.dtstyle import parse_dtstyle
from chemigram.core.versioning import ImageRepo, xmp_hash
from chemigram.core.versioning.ops import (
    branch,
    checkout,
    diff,
    log,
    snapshot,
    tag,
)
from chemigram.core.xmp import parse_xmp, synthesize_xmp

_FIXTURES = Path(__file__).resolve().parents[4] / "tests" / "fixtures"


def test_full_workflow_against_v3_reference(tmp_path: Path) -> None:
    repo = ImageRepo.init(tmp_path / "repo")

    # Snapshot the v3 baseline
    baseline = parse_xmp(_FIXTURES / "xmps" / "synthesized_v3_reference.xmp")
    h_baseline = snapshot(repo, baseline, label="v3-baseline")
    assert repo.resolve_ref("refs/heads/main") == h_baseline

    # Branch and switch
    branch(repo, "experimental")
    checkout(repo, "experimental")
    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/experimental"

    # Apply a vocabulary primitive (replaces the +2.0 EV exposure with +0.5)
    expo_plus = parse_dtstyle(_FIXTURES / "dtstyles" / "expo_plus_0p5.dtstyle")
    modified = synthesize_xmp(baseline, [expo_plus])
    h_modified = snapshot(repo, modified, label="expo+0.5")
    assert h_modified != h_baseline
    assert repo.resolve_ref("refs/heads/experimental") == h_modified

    # Tag the modified state
    tag(repo, "expo-plus-0p5-applied", hash_=h_modified)
    assert repo.resolve_ref("refs/tags/expo-plus-0p5-applied") == h_modified

    # Diff baseline vs modified — exposure entry's params should differ
    deltas = diff(repo, h_baseline, h_modified)
    exposure_diffs = [d for d in deltas if d.operation == "exposure"]
    assert len(exposure_diffs) == 1
    assert exposure_diffs[0].kind == "changed"
    assert "00000040" in (exposure_diffs[0].a_params or "")  # +2.0 EV
    assert "0000003f" in (exposure_diffs[0].b_params or "")  # +0.5 EV

    # Checkout main, verify we get the original
    checkout(repo, "main")
    main_xmp = checkout(repo, h_baseline)
    assert xmp_hash(main_xmp) == h_baseline

    # Log shows all operations newest first
    entries = log(repo)
    ops = [e.op for e in entries]
    # We did: snapshot, branch, checkout, snapshot, tag, checkout, checkout
    assert ops[0] == "checkout"
    assert "tag" in ops
    assert "branch" in ops
    assert ops.count("snapshot") == 2
