"""Tests for the structured logging module."""

import inspect
import json
import logging

import pytest

from climate_impacts_mcp.logging import GCPJsonFormatter, _sanitize_args, log_tool_call


# --- GCPJsonFormatter tests ---


class TestGCPJsonFormatter:
    def _make_record(self, msg="test", level=logging.INFO, **extra):
        logger = logging.getLogger("test")
        record = logger.makeRecord("test", level, "test.py", 1, msg, (), None)
        for k, v in extra.items():
            setattr(record, k, v)
        return record

    def test_basic_format_is_valid_json(self):
        formatter = GCPJsonFormatter()
        record = self._make_record("hello")
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["severity"] == "INFO"
        assert parsed["message"] == "hello"
        assert "timestamp" in parsed
        assert parsed["logger"] == "test"

    def test_extra_fields_included(self):
        formatter = GCPJsonFormatter()
        record = self._make_record(
            "Tool call completed",
            tool="get_climate_projections",
            arguments={"country": "DEU"},
            duration_ms=123.4,
            success=True,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["tool"] == "get_climate_projections"
        assert parsed["arguments"] == {"country": "DEU"}
        assert parsed["duration_ms"] == 123.4
        assert parsed["success"] is True

    def test_missing_extra_fields_omitted(self):
        formatter = GCPJsonFormatter()
        record = self._make_record("simple message")
        parsed = json.loads(formatter.format(record))
        assert "tool" not in parsed
        assert "arguments" not in parsed
        assert "duration_ms" not in parsed

    def test_error_level(self):
        formatter = GCPJsonFormatter()
        record = self._make_record("fail", level=logging.ERROR, error="something broke")
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "ERROR"
        assert parsed["error"] == "something broke"

    def test_exception_info_overrides_severity(self):
        formatter = GCPJsonFormatter()
        try:
            raise ValueError("bad value")
        except ValueError:
            import sys

            record = self._make_record("fail", level=logging.INFO)
            record.exc_info = sys.exc_info()
        parsed = json.loads(formatter.format(record))
        assert parsed["severity"] == "ERROR"
        assert "bad value" in parsed["error"]


# --- _sanitize_args tests ---


class TestSanitizeArgs:
    async def _dummy_tool(self, ctx, country: str, variable: str = "tasAdjust"):
        pass

    def test_excludes_ctx(self):
        async def my_tool(ctx, country: str):
            pass

        result = _sanitize_args(my_tool, (object(), "DEU"), {})
        assert "ctx" not in result
        assert result["country"] == "DEU"

    def test_includes_defaults(self):
        async def my_tool(ctx, country: str, variable: str = "tasAdjust"):
            pass

        result = _sanitize_args(my_tool, (object(), "DEU"), {})
        assert result == {"country": "DEU", "variable": "tasAdjust"}

    def test_kwargs(self):
        async def my_tool(ctx, country: str):
            pass

        result = _sanitize_args(my_tool, (object(),), {"country": "FRA"})
        assert result == {"country": "FRA"}


# --- log_tool_call decorator tests ---


class TestLogToolCall:
    async def test_success_logging(self, caplog):
        async def my_tool(ctx, country: str) -> str:
            """My tool docstring."""
            return f"result for {country}"

        wrapped = log_tool_call(my_tool)

        with caplog.at_level(logging.INFO, logger="climate_impacts_mcp.tools"):
            result = await wrapped(None, country="DEU")

        assert result == "result for DEU"
        assert any("Tool call completed" in r.message for r in caplog.records)
        record = next(r for r in caplog.records if r.message == "Tool call completed")
        assert record.tool == "my_tool"
        assert record.arguments == {"country": "DEU"}
        assert record.success is True
        assert record.duration_ms >= 0

    async def test_error_logging(self, caplog):
        async def failing_tool(ctx) -> str:
            raise ValueError("something went wrong")

        wrapped = log_tool_call(failing_tool)

        with caplog.at_level(logging.ERROR, logger="climate_impacts_mcp.tools"):
            with pytest.raises(ValueError, match="something went wrong"):
                await wrapped(None)

        record = next(r for r in caplog.records if r.message == "Tool call failed")
        assert record.tool == "failing_tool"
        assert record.success is False
        assert record.error == "something went wrong"

    async def test_preserves_function_metadata(self):
        async def my_tool(ctx, country: str, variable: str = "tasAdjust") -> str:
            """Docstring for my_tool."""
            return ""

        wrapped = log_tool_call(my_tool)
        assert wrapped.__name__ == "my_tool"
        assert wrapped.__doc__ == "Docstring for my_tool."
        # inspect.signature should see the original signature, not *args/**kwargs
        sig = inspect.signature(wrapped)
        assert "ctx" in sig.parameters
        assert "country" in sig.parameters
        assert "variable" in sig.parameters
