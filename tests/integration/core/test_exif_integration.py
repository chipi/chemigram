"""Integration test: read EXIF from the real Phase 0 D850 NEF.

Skips cleanly when ``CHEMIGRAM_TEST_RAW`` is unset and the default
``~/chemigram-phase0/raws/raw-test.NEF`` is absent.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from chemigram.core.exif import read_exif

_DEFAULT_RAW = Path.home() / "chemigram-phase0" / "raws" / "raw-test.NEF"


def _resolve_raw() -> Path | None:
    env = os.environ.get("CHEMIGRAM_TEST_RAW")
    if env:
        path = Path(env).expanduser()
        return path if path.exists() else None
    return _DEFAULT_RAW if _DEFAULT_RAW.exists() else None


@pytest.fixture(scope="module")
def test_raw() -> Path:
    raw = _resolve_raw()
    if raw is None:
        pytest.skip(f"no usable test raw ($CHEMIGRAM_TEST_RAW unset and {_DEFAULT_RAW} absent)")
    return raw


def test_real_d850_exif_round_trip(test_raw: Path) -> None:
    exif = read_exif(test_raw)
    assert exif.make
    assert exif.model
    # Phase 0 calibration: the reference NEF is from a Nikon D850
    assert "NIKON" in exif.make.upper()
    assert "D850" in exif.model.upper()
