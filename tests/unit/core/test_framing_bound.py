"""Tests for the canonical framing-bound op registry.

The registry (chemigram.core.framing_bound.FRAMING_BOUND_OPS) is the
single source of truth for "ops that don't propagate cleanly across
images". Documents the v1.10.0 baseline; flags any accidental
membership change.
"""

from __future__ import annotations

from chemigram.core.framing_bound import FRAMING_BOUND_OPS, is_framing_bound_op


def test_canonical_framing_bound_membership() -> None:
    """The v1.10.0 baseline. Adding/removing an op should be a deliberate
    decision; this test documents the current set."""
    expected = {"crop", "ashift", "retouch", "lens"}
    assert FRAMING_BOUND_OPS == expected, (
        f"FRAMING_BOUND_OPS membership changed: got {FRAMING_BOUND_OPS}, "
        f"expected {expected}. If intentional, update this test and the "
        f"docstring of chemigram.core.framing_bound."
    )


def test_is_framing_bound_op_function_form() -> None:
    """``is_framing_bound_op()`` is a thin alias for the membership check."""
    assert is_framing_bound_op("crop")
    assert is_framing_bound_op("ashift")
    assert is_framing_bound_op("retouch")
    assert is_framing_bound_op("lens")
    assert not is_framing_bound_op("exposure")
    assert not is_framing_bound_op("colorequal")
    assert not is_framing_bound_op("sigmoid")
    assert not is_framing_bound_op("not-a-real-op")


def test_propagate_re_exports_for_backcompat() -> None:
    """``from chemigram.core.propagate import FRAMING_BOUND_OPS`` must still
    work (was the original location pre-Gap-D-closure)."""
    import chemigram.core.framing_bound as framing_bound_mod
    import chemigram.core.propagate as propagate_mod

    assert propagate_mod.FRAMING_BOUND_OPS is framing_bound_mod.FRAMING_BOUND_OPS, (
        "propagate.FRAMING_BOUND_OPS must be the same frozenset object as "
        "the canonical one in framing_bound.py — re-export, not re-define"
    )
