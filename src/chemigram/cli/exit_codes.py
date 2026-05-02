"""Exit-code IntEnum for the chemigram CLI (RFC-020 §D).

The set is closed; new codes go through ADR-072 amendments. Each
``ErrorCode`` from :mod:`chemigram.mcp.errors` maps to exactly one
non-zero ``ExitCode`` in :mod:`chemigram.cli.error_mapping`.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Stable, documented exit codes for the chemigram CLI.

    Agents shelling out to the CLI branch on the numeric code without
    parsing stderr text. The set mirrors ``chemigram.mcp.errors.ErrorCode``
    plus a ``SUCCESS`` and a catch-all ``INTERNAL_ERROR`` for unhandled
    exceptions (those are bugs).
    """

    SUCCESS = 0
    INTERNAL_ERROR = 1
    INVALID_INPUT = 2
    NOT_FOUND = 3
    STATE_ERROR = 4
    VERSIONING_ERROR = 5
    DARKTABLE_ERROR = 6
    MASKING_ERROR = 7
    SYNTHESIZER_ERROR = 8
    PERMISSION_ERROR = 9
    NOT_IMPLEMENTED = 10
