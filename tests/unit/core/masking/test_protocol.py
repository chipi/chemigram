"""Unit tests for chemigram.core.masking — Protocol + MaskResult shape."""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.masking import (
    MaskFormatError,
    MaskGenerationError,
    MaskingError,
    MaskingProvider,
    MaskResult,
)


def test_mask_result_shape() -> None:
    r = MaskResult(
        png_bytes=b"\x89PNG\r\n\x1a\n",
        generator="x",
        prompt=None,
        target="manta",
    )
    assert r.target == "manta"
    assert r.generator == "x"
    assert r.prompt is None


def test_mask_result_frozen() -> None:
    r = MaskResult(png_bytes=b"", generator="x", prompt=None, target="t")
    with pytest.raises((AttributeError, TypeError)):
        r.target = "other"  # type: ignore[misc]


def test_error_hierarchy() -> None:
    assert issubclass(MaskGenerationError, MaskingError)
    assert issubclass(MaskFormatError, MaskingError)


def test_fake_provider_satisfies_protocol() -> None:
    """A hand-rolled fake conforms to the Protocol shape."""

    class FakeProvider:
        def generate(
            self,
            *,
            target: str,
            render_path: Path,
            prompt: str | None = None,
        ) -> MaskResult:
            return MaskResult(
                png_bytes=b"\x89PNG\r\n\x1a\n",
                generator="fake",
                prompt=prompt,
                target=target,
            )

        def regenerate(
            self,
            *,
            target: str,
            render_path: Path,
            prior_mask: bytes,
            prompt: str | None = None,
        ) -> MaskResult:
            return self.generate(target=target, render_path=render_path, prompt=prompt)

    fake: MaskingProvider = FakeProvider()
    out = fake.generate(target="t", render_path=Path("dummy.png"))
    assert out.target == "t"
