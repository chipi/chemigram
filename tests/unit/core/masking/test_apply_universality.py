"""Mask apply path is universal: every loaded vocab entry can be mask-bound.

This test guards the promise that any vocabulary primitive — not just the
4 currently-shipped mask-bound entries in ``expressive-baseline/L3/masked/`` —
can be applied through a drawn mask via :func:`apply_with_drawn_mask`.

The mechanism is generic: the helper patches each plugin's 420-byte
``blendop_params`` blob to bind the form, then injects ``masks_history``
into the XMP. Any module whose ``blendop_params`` decodes to that canonical
size gets a working drawn-mask binding for free — no per-module
engineering needed.

What this catches:

- A future vocabulary entry shipping with a non-420-byte blendop blob
  (older or newer ``dt_develop_blend_params_t`` revision), which would
  raise inside :func:`patch_blendop_params_string`.
- A mask_spec encoder regression that breaks form serialization for one
  of the three drawn forms.

What this doesn't cover (out of scope, covered elsewhere):

- Whether darktable actually localizes the effect at render time — that
  belongs in the lab-grade e2e tests
  (:mod:`tests.e2e.test_lab_grade_masked_primitives`), which render
  through real darktable and assert spatial localization.
- Module-pipeline-position quirks (e.g., temperature runs early in the
  raw pipeline so its drawn-mask behavior on display-referred chart
  input differs from real-raw input). The unit test only checks that
  the apply path completes; the e2e test checks the photographic result.
"""

from __future__ import annotations

import dataclasses

import pytest

from chemigram.core.helpers import apply_with_drawn_mask
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp

_GRADIENT_SPEC = {
    "dt_form": "gradient",
    "dt_params": {"anchor_x": 0.5, "anchor_y": 0.5, "rotation": 0.0, "compression": 0.5},
}
_ELLIPSE_SPEC = {
    "dt_form": "ellipse",
    "dt_params": {
        "center_x": 0.5,
        "center_y": 0.5,
        "radius_x": 0.25,
        "radius_y": 0.25,
        "border": 0.05,
    },
}
_RECTANGLE_SPEC = {
    "dt_form": "rectangle",
    "dt_params": {"x0": 0.2, "y0": 0.2, "x1": 0.8, "y1": 0.8, "border": 0.02},
}


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["starter", "expressive-baseline"])


@pytest.fixture(scope="module")
def empty_baseline() -> Xmp:
    """Empty-history baseline so the synthesizer's only output is the entry under test."""
    from pathlib import Path

    template = parse_xmp(
        Path(__file__).resolve().parents[4] / "src/chemigram/core/_baseline_v1.xmp"
    )
    return dataclasses.replace(template, history=())


@pytest.mark.parametrize(
    "spec,form_label",
    [
        (_GRADIENT_SPEC, "gradient"),
        (_ELLIPSE_SPEC, "ellipse"),
        (_RECTANGLE_SPEC, "rectangle"),
    ],
    ids=["gradient", "ellipse", "rectangle"],
)
def test_every_entry_accepts_every_drawn_form(
    vocab: VocabularyIndex,
    empty_baseline: Xmp,
    spec: dict,
    form_label: str,
) -> None:
    """For every loaded vocab entry x every drawn form: apply path completes
    and produces an XMP with patched blendop_params + masks_history.

    Skips the 4 entries that already carry a ``mask_spec`` (mask-bound
    primitives) — those are tested via their own native specs in the
    lab-grade e2e suite, and re-binding them here would shadow their
    intended geometry without adding new coverage.
    """
    for entry in vocab.list_all():
        if entry.mask_spec is not None:
            continue  # mask-bound entries: covered by their own spec elsewhere
        # Every plugin's blendop_params must decode to the canonical 420-byte
        # size for the apply path to succeed; failure here is an authoring bug
        # we want surfaced before runtime.
        result = apply_with_drawn_mask(empty_baseline, entry.dtstyle, spec)

        # Effect of the entry is present (history grew by one plugin per touched module).
        n_expected = len(entry.dtstyle.plugins)
        n_actual = len(result.history)
        assert n_actual == n_expected, (
            f"{entry.name}: expected {n_expected} plugins, got {n_actual}"
        )

        # All plugin blendop blobs were patched (mask-mode flag bytes != default).
        # Cheap structural check — full decoding lives in test_dt_serialize.
        for plug in result.history:
            assert plug.blendop_params.startswith("gz"), (
                f"{entry.name}/{plug.operation}: expected gz-encoded blob, "
                f"got {plug.blendop_params[:8]!r}"
            )

        # masks_history was injected for the form to actually wire up.
        masks_elems = [
            value
            for kind, qname, value in result.raw_extra_fields
            if kind == "elem" and qname == "darktable:masks_history"
        ]
        assert len(masks_elems) == 1, (
            f"{entry.name} ({form_label}): expected 1 masks_history elem, got {len(masks_elems)}"
        )
        assert 'darktable:mask_type="' in masks_elems[0], (
            f"{entry.name}: masks_history XML missing mask_type attribute"
        )


def test_no_entry_has_unsupported_blendop_size(vocab: VocabularyIndex) -> None:
    """Every loaded plugin's blendop blob must decode to 420 bytes.

    If this fails, a vocabulary contributor shipped an entry authored
    against a different darktable blendop schema. Fix by re-authoring the
    entry against darktable 5.4.x or by updating the blendop encoder to
    handle the new size (and bumping ``DT_MASKS_VERSION`` accordingly).
    """
    from chemigram.core.masking.dt_serialize import (
        _BLEND_PARAMS_SIZE,
        _decode_default_blendop_blob,
    )

    offenders: list[str] = []
    for entry in vocab.list_all():
        for plug in entry.dtstyle.plugins:
            bp = plug.blendop_params
            try:
                raw = _decode_default_blendop_blob(bp) if bp.startswith("gz") else bytes.fromhex(bp)
            except Exception as exc:
                offenders.append(f"{entry.name}/{plug.operation}: decode error {exc}")
                continue
            if len(raw) != _BLEND_PARAMS_SIZE:
                offenders.append(
                    f"{entry.name}/{plug.operation}: {len(raw)} bytes "
                    f"(expected {_BLEND_PARAMS_SIZE})"
                )
    if offenders:
        pytest.fail(
            "Vocab entries with non-canonical blendop_params size — these will\n"
            "fail apply_with_drawn_mask. Re-author against darktable 5.4.x:\n  "
            + "\n  ".join(offenders)
        )
