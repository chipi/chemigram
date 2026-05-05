"""Integration: parameterized exposure apply path end-to-end.

Closes part of RFC-021 / ADR-077..080: the apply path in
``chemigram.core.helpers.apply_entry`` accepts ``parameter_values``,
patches the dtstyle's ``op_params`` via the Path C decoder, synthesizes
a valid XMP, and (on a fresh round-trip through write/parse) carries
the patched bytes intact.

Composition coverage: parameter values + drawn-mask binding together
produce a single XMP with both axes applied.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.exposure import decode
from chemigram.core.vocab import (
    load_packs,
)
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def parameterized_exposure_entry():
    """The shipped parameterized ``exposure`` entry from the
    expressive-baseline pack. Post-v1.6.0 the manifest declares the
    ``parameters`` block; this fixture loads it directly so the
    integration test exercises the production manifest path."""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("exposure")
    assert entry is not None
    assert entry.parameters is not None, "exposure entry missing 'parameters' declaration"
    return entry


@pytest.mark.parametrize("ev", [-3.0, -1.0, -0.5, 0.0, 0.5, 1.0, 3.0])
def test_apply_entry_with_parameter_value_patches_op_params(
    baseline_xmp, parameterized_exposure_entry, ev: float
) -> None:
    """Applying the parameterized exposure entry with ``ev=v`` produces
    an XMP whose exposure plugin's op_params decode to that EV."""
    new_xmp = apply_entry(baseline_xmp, parameterized_exposure_entry, parameter_values={"ev": ev})
    exposure_plugins = [p for p in new_xmp.history if p.operation == "exposure"]
    assert exposure_plugins, "no exposure plugin found in synthesized XMP history"
    # The most-recently-added plugin (last entry) is the one we just applied.
    fields = decode(exposure_plugins[-1].params)
    assert fields[2] == pytest.approx(ev, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, parameterized_exposure_entry, tmp_path: Path
) -> None:
    """The patched op_params survive a full write→parse cycle."""
    new_xmp = apply_entry(baseline_xmp, parameterized_exposure_entry, parameter_values={"ev": 0.7})
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)

    text = out_path.read_text()
    # Find the most-recent exposure op_params via regex. The XMP writer
    # serializes ``op_params`` as the ``darktable:params`` XML attribute
    # (rename happens at the writer; the dtstyle field stays ``op_params``).
    matches = re.findall(
        r'darktable:operation="exposure"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches, "no exposure op_params in serialized XMP"
    fields = decode(matches[-1])
    assert fields[2] == pytest.approx(0.7, abs=1e-5)

    # Re-parse and re-extract; should still hold
    parsed = parse_xmp(out_path)
    re_exposure = [p for p in parsed.history if p.operation == "exposure"]
    assert re_exposure
    fields = decode(re_exposure[-1].params)
    assert fields[2] == pytest.approx(0.7, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_defaults(
    baseline_xmp, parameterized_exposure_entry
) -> None:
    """Without parameter_values, the apply path is equivalent to plain
    synthesize — the dtstyle's existing op_params bytes carry through.
    The shipped exposure.dtstyle has ev=0.0 (the parameter default)."""
    no_param_xmp = apply_entry(baseline_xmp, parameterized_exposure_entry)
    expo_plugins = [p for p in no_param_xmp.history if p.operation == "exposure"]
    assert expo_plugins
    fields = decode(expo_plugins[-1].params)
    assert fields[2] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_with_parameter_and_mask_composes(
    baseline_xmp, parameterized_exposure_entry
) -> None:
    """Both axes (parameter values + drawn mask) compose: the resulting
    XMP carries the patched op_params AND a masks_history element."""
    mask_spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.5,
            "center_y": 0.5,
            "radius_x": 0.3,
            "radius_y": 0.3,
            "border": 0.05,
        },
    }
    new_xmp = apply_entry(
        baseline_xmp,
        parameterized_exposure_entry,
        parameter_values={"ev": 1.2},
        mask_spec=mask_spec,
    )

    # Exposure op_params is patched (axis 1)
    expo_plugins = [p for p in new_xmp.history if p.operation == "exposure"]
    assert expo_plugins
    fields = decode(expo_plugins[-1].params)
    assert fields[2] == pytest.approx(1.2, abs=1e-5)

    # masks_history is injected (axis 2)
    masks_elems = [
        v
        for kind, qname, v in new_xmp.raw_extra_fields
        if kind == "elem" and qname == "darktable:masks_history"
    ]
    assert len(masks_elems) == 1
    assert 'darktable:mask_type="' in masks_elems[0]


def test_apply_entry_unknown_param_name_silently_ignored(
    baseline_xmp, parameterized_exposure_entry
) -> None:
    """Caller passing an unknown param name (e.g. typo) is ignored; the
    range/name validation is the CLI/MCP adapter's responsibility, not
    the engine's. The engine just patches what it can match.

    (This test documents the contract; the CLI adapter will reject
    unknown param names with INVALID_INPUT before reaching this layer.)
    """
    new_xmp = apply_entry(
        baseline_xmp,
        parameterized_exposure_entry,
        parameter_values={"ev": 0.5, "nonexistent": 99.0},
    )
    expo_plugins = [p for p in new_xmp.history if p.operation == "exposure"]
    assert expo_plugins
    fields = decode(expo_plugins[-1].params)
    assert fields[2] == pytest.approx(0.5, abs=1e-5)


def test_apply_entry_rejects_parameter_values_on_non_parameterized_entry(
    baseline_xmp,
) -> None:
    """Calling with parameter_values on an entry without parameters
    declaration is a TypeError (caller bug). ``wb_warm_subtle`` is a
    starter entry with no parameters block."""
    from chemigram.core.vocab import load_starter

    index = load_starter()
    plain_entry = index.lookup_by_name("wb_warm_subtle")
    assert plain_entry is not None
    assert plain_entry.parameters is None
    with pytest.raises(TypeError, match="no 'parameters' declaration"):
        apply_entry(baseline_xmp, plain_entry, parameter_values={"ev": 0.5})
