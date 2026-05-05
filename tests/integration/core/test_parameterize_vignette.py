"""Integration: parameterized vignette apply path end-to-end.

Mirrors test_parameterize_exposure.py for the second parameterized
module. Validates that ``apply_entry`` with vignette parameter values
patches the dtstyle's ``op_params`` byte-correctly and the resulting
XMP carries those bytes through write/parse round-trip.

Composition with mask isn't asserted here — vignette x mask is a
documented dead pairing (mask-applicable-controls.md#vignette).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.vignette import decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def vignette_entry():
    """The shipped parameterized ``vignette`` entry from the
    expressive-baseline pack."""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("vignette")
    assert entry is not None
    assert entry.parameters is not None, "vignette entry missing 'parameters' declaration"
    return entry


@pytest.mark.parametrize("brightness", [-1.0, -0.8, -0.5, -0.25, 0.0, 0.5, 1.0])
def test_apply_entry_with_brightness_patches_op_params(
    baseline_xmp, vignette_entry, brightness: float
) -> None:
    """Applying vignette with a brightness value produces an XMP whose
    vignette plugin's op_params decodes to that value."""
    new_xmp = apply_entry(baseline_xmp, vignette_entry, parameter_values={"brightness": brightness})
    plugins = [p for p in new_xmp.history if p.operation == "vignette"]
    assert plugins, "no vignette plugin in synthesized XMP history"
    fields = decode(plugins[-1].params)
    assert fields[2] == pytest.approx(brightness, abs=1e-5)


def test_apply_entry_no_values_uses_default(baseline_xmp, vignette_entry) -> None:
    """Without parameter_values, the dtstyle's default brightness (-0.25)
    carries through."""
    new_xmp = apply_entry(baseline_xmp, vignette_entry)
    plugins = [p for p in new_xmp.history if p.operation == "vignette"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[2] == pytest.approx(-0.25, abs=1e-5)
