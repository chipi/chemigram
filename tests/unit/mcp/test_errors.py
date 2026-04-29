"""Unit tests for chemigram.mcp.errors — RFC-010 contract types."""

from __future__ import annotations

import json

from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
    error_not_implemented,
)


def test_tool_result_ok_shape() -> None:
    r: ToolResult[dict] = ToolResult.ok({"head_hash": "abc"})
    assert r.success is True
    assert r.data == {"head_hash": "abc"}
    assert r.error is None


def test_tool_result_fail_shape() -> None:
    err = ToolError(code=ErrorCode.NOT_FOUND, message="x")
    r: ToolResult[None] = ToolResult.fail(err)
    assert r.success is False
    assert r.data is None
    assert r.error is err


def test_tool_result_payload_ok() -> None:
    r = ToolResult.ok({"k": "v"})
    payload = r.to_payload()
    assert payload == {"success": True, "data": {"k": "v"}, "error": None}
    # round-trips through json
    assert json.loads(json.dumps(payload)) == payload


def test_tool_result_payload_fail_includes_str_code() -> None:
    err = ToolError(
        code=ErrorCode.DARKTABLE_ERROR,
        message="boom",
        details={"stderr": "..."},
        recoverable=True,
    )
    payload = ToolResult.fail(err).to_payload()
    assert payload["success"] is False
    assert payload["error"]["code"] == "darktable_error"
    assert payload["error"]["message"] == "boom"
    assert payload["error"]["details"] == {"stderr": "..."}
    assert payload["error"]["recoverable"] is True


def test_error_code_values() -> None:
    expected = {
        "invalid_input",
        "not_found",
        "darktable_error",
        "synthesizer_error",
        "versioning_error",
        "masking_error",
        "permission_error",
        "state_error",
        "not_implemented",
    }
    assert {str(c) for c in ErrorCode} == expected


def test_error_invalid_input_helper() -> None:
    err = error_invalid_input("must be int", got="str")
    assert err.code == ErrorCode.INVALID_INPUT
    assert err.details == {"got": "str"}


def test_error_not_found_helper() -> None:
    err = error_not_found("image abc")
    assert err.code == ErrorCode.NOT_FOUND
    assert "abc" in err.message


def test_error_not_implemented_helper_with_slice() -> None:
    err = error_not_implemented("masking lands later", slice=4)
    assert err.code == ErrorCode.NOT_IMPLEMENTED
    assert err.details == {"slice": 4}
    assert err.recoverable is False
