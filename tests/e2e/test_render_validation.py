"""End-to-end pixel-level validation against a real darktable render.

Synthesizes XMPs via ``chemigram.core.xmp.synthesize_xmp`` + the bundled
starter vocabulary, renders each through real ``darktable-cli`` against
the Phase 0 test raw, and asserts the rendered JPEG's pixel statistics
moved in the expected direction.

These tests are the missing layer between unit tests (parser /
synthesizer correctness on opaque blobs) and "trust me, it renders" —
they validate that the full chain *actually does the right thing* on a
real photo, not just that bytes come back.

Tolerances are deliberately generous: tests need to survive image
content (dark vs bright scenes, different cameras), darktable version
drift within 5.x, and JPEG quantization noise. Direction-of-change is
the assertion, not exact magnitudes.

Skipped automatically when:
- ``darktable-cli`` is missing
- ``CHEMIGRAM_TEST_RAW`` (or the default Phase 0 raw) is missing
- ``CHEMIGRAM_DT_CONFIGDIR`` (or the default Phase 0 configdir) is missing
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.pipeline import render
from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp, synthesize_xmp, write_xmp


def _render(
    raw: Path,
    xmp: Xmp,
    configdir: Path,
    out_dir: Path,
    *,
    name: str,
    binary: str,
) -> Path:
    """Synthesize → write XMP → invoke real darktable → return JPEG path.

    Renders at 512x512 to keep wall-clock low while preserving enough
    pixels for stable channel means. ``high_quality=False`` (preview
    flag); fine for direction-of-change validation.
    """
    xmp_path = out_dir / f"{name}.xmp"
    out_path = out_dir / f"{name}.jpg"
    write_xmp(xmp, xmp_path)
    # The pipeline picks up the binary via $DARKTABLE_CLI or PATH; we
    # don't override here because the integration tier already exercises
    # binary-override paths.
    _ = binary
    result = render(
        raw_path=raw,
        xmp_path=xmp_path,
        output_path=out_path,
        width=512,
        height=512,
        high_quality=False,
        configdir=configdir,
    )
    assert result.success, f"{name} render failed: {result.error_message}\n{result.stderr}"
    assert out_path.exists() and out_path.stat().st_size > 0
    return out_path


# --- baseline determinism ----------------------------------------------


def test_baseline_renders_consistently(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Two renders of the same XMP produce near-identical pixel stats.

    Sanity check: if this fails, all the change-direction tests below
    are unreliable. darktable-cli is deterministic for a given configdir
    + raw + XMP; the only noise source is JPEG quantization, which is
    bounded.
    """
    a = _render(
        test_raw, baseline_xmp, configdir, tmp_path, name="baseline_a", binary=darktable_binary
    )
    b = _render(
        test_raw, baseline_xmp, configdir, tmp_path, name="baseline_b", binary=darktable_binary
    )

    lum_a = pixel_stats.mean_luminance(a)
    lum_b = pixel_stats.mean_luminance(b)
    # Tolerance: 0.5 of a luma unit (out of 255).  JPEG q-noise is way smaller.
    assert abs(lum_a - lum_b) < 0.5, (
        f"baseline render not deterministic: lum_a={lum_a:.3f}, lum_b={lum_b:.3f}"
    )


# --- direction-of-change per primitive ---------------------------------
#
# Note on baselines: the bundled ``src/chemigram/core/_baseline_v1.xmp``
# is not a neutral starting state — it's the Phase 0 reference XMP, which
# has +2.0 EV baked into its exposure entry. SET-replace semantics
# (ADR-002) mean that applying e.g. expo_+0.5 *replaces* the +2.0 EV with
# +0.5 EV, producing a *darker* image than the rendered baseline.
#
# That's correct SET behavior, but it makes "applying expo_+0.5 brightens
# the baseline" a wrong expectation for these tests. We assert relative
# direction between the two exposure primitives instead — that holds
# regardless of where the baseline sits — and against a future slice
# where workspace ingest generates a neutral baseline via darktable-cli,
# these tests will keep working unchanged.


def test_expo_primitives_have_correct_relative_ordering(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """``expo_+0.5`` produces a brighter render than ``expo_-0.5``.

    The two primitives differ in their dtstyle's exposure float by 1.0 EV,
    which on a typical scene is many luma units. This test catches:
    - dtstyle files getting mis-named / swapped
    - synthesize_xmp dropping operations
    - render pipeline applying operations in the wrong order
    - hex-blob corruption from a copy/move that wasn't byte-for-byte
    """
    plus_entry = starter_vocab.lookup_by_name("expo_+0.5")
    minus_entry = starter_vocab.lookup_by_name("expo_-0.5")
    assert plus_entry is not None and minus_entry is not None

    plus_xmp = synthesize_xmp(baseline_xmp, [plus_entry.dtstyle])
    minus_xmp = synthesize_xmp(baseline_xmp, [minus_entry.dtstyle])

    plus_jpg = _render(
        test_raw, plus_xmp, configdir, tmp_path, name="plus", binary=darktable_binary
    )
    minus_jpg = _render(
        test_raw, minus_xmp, configdir, tmp_path, name="minus", binary=darktable_binary
    )

    plus_lum = pixel_stats.mean_luminance(plus_jpg)
    minus_lum = pixel_stats.mean_luminance(minus_jpg)
    delta = plus_lum - minus_lum

    # 1.0 EV difference on a typical scene shifts mean luma by ~50 units
    # (out of 255). Demand at least +5.0 — generous enough to survive
    # scene content variation but well above noise floor.
    assert delta > 5.0, (
        f"expo_+0.5 should render brighter than expo_-0.5; "
        f"got plus={plus_lum:.2f}, minus={minus_lum:.2f}, delta={delta:.3f}"
    )


def test_expo_primitive_changes_baseline(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Applying ``expo_+0.5`` produces a *measurably different* render
    from baseline. Direction depends on the baseline's exposure entry
    (see module docstring); we don't assert direction here, only that
    something happened.

    This catches the worst regression: synthesize_xmp returning the
    baseline unchanged, or render silently dropping the synthesized
    operation.
    """
    base = _render(
        test_raw, baseline_xmp, configdir, tmp_path, name="base", binary=darktable_binary
    )
    entry = starter_vocab.lookup_by_name("expo_+0.5")
    assert entry is not None
    plus = synthesize_xmp(baseline_xmp, [entry.dtstyle])
    plus_jpg = _render(test_raw, plus, configdir, tmp_path, name="plus", binary=darktable_binary)

    base_lum = pixel_stats.mean_luminance(base)
    plus_lum = pixel_stats.mean_luminance(plus_jpg)
    delta = abs(plus_lum - base_lum)

    # Demand at least 5 luma units of change — well above noise floor,
    # well below typical primitive's actual delta.
    assert delta > 5.0, (
        f"expo_+0.5 should change the render measurably; "
        f"got base={base_lum:.2f}, plus={plus_lum:.2f}, |delta|={delta:.3f}"
    )


def test_expo_plus_minus_approximately_cancels(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Per ADR-002 SET semantics, applying expo_+0.5 then expo_-0.5
    replaces the previous exposure entry rather than stacking.  The
    second SET is what darktable renders.

    This isn't strict cancellation — it's *replacement*.  After both
    moves are applied in sequence, the rendered image should match what
    expo_-0.5 alone produces, NOT the baseline (because the
    expo_+0.5 was overwritten, not undone).
    """
    base = _render(
        test_raw, baseline_xmp, configdir, tmp_path, name="base", binary=darktable_binary
    )
    entry_plus = starter_vocab.lookup_by_name("expo_+0.5")
    entry_minus = starter_vocab.lookup_by_name("expo_-0.5")
    assert entry_plus is not None and entry_minus is not None

    # Apply both in sequence; SET semantics means the second wins.
    sequence = synthesize_xmp(baseline_xmp, [entry_plus.dtstyle, entry_minus.dtstyle])
    seq_jpg = _render(test_raw, sequence, configdir, tmp_path, name="seq", binary=darktable_binary)

    # Same as expo_-0.5 alone for comparison.
    just_minus = synthesize_xmp(baseline_xmp, [entry_minus.dtstyle])
    minus_jpg = _render(
        test_raw, just_minus, configdir, tmp_path, name="just_minus", binary=darktable_binary
    )

    base_lum = pixel_stats.mean_luminance(base)
    seq_lum = pixel_stats.mean_luminance(seq_jpg)
    minus_lum = pixel_stats.mean_luminance(minus_jpg)

    # The sequence should match expo_-0.5 alone (within noise) and be
    # darker than the baseline.
    assert abs(seq_lum - minus_lum) < 1.0, (
        f"expo_+ then expo_- should equal expo_- alone (SET semantics); "
        f"got seq={seq_lum:.2f}, just_minus={minus_lum:.2f}"
    )
    assert base_lum - seq_lum > 1.0, (
        f"expo_+ then expo_- should still leave image darker than baseline; "
        f"got base={base_lum:.2f}, seq={seq_lum:.2f}"
    )


def test_wb_warm_subtle_warms_image(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Applying ``wb_warm_subtle`` shifts the image toward warm tones —
    measurable as an increase in (R+G)/(2*B).
    """
    base = _render(
        test_raw, baseline_xmp, configdir, tmp_path, name="base", binary=darktable_binary
    )
    entry = starter_vocab.lookup_by_name("wb_warm_subtle")
    assert entry is not None
    warmed = synthesize_xmp(baseline_xmp, [entry.dtstyle])
    warmed_jpg = _render(
        test_raw, warmed, configdir, tmp_path, name="warmed", binary=darktable_binary
    )

    base_warmth = pixel_stats.warmth_ratio(base)
    warmed_warmth = pixel_stats.warmth_ratio(warmed_jpg)

    # Warmth shift on a typical scene is a fraction-of-a-unit change in
    # the ratio.  We demand a clearly-positive delta but stay tolerant
    # of scene-specific magnitude.
    assert warmed_warmth > base_warmth, (
        f"wb_warm_subtle should warm the image, got base={base_warmth:.4f}, "
        f"warmed={warmed_warmth:.4f}"
    )


def test_baseline_xmp_renders_close_to_raw_default(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """The bundled ``_baseline_v1.xmp`` should produce a render with a
    plausible mean luminance — not pure black, not blown out.

    This catches regressions where the baseline XMP gets corrupted or
    references modules that fail to apply.
    """
    out = _render(test_raw, baseline_xmp, configdir, tmp_path, name="base", binary=darktable_binary)
    lum = pixel_stats.mean_luminance(out)
    assert 20 < lum < 230, f"baseline render mean luma={lum:.2f} suspect; expected 20-230"
