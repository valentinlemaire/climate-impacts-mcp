"""Structured JSON logging for GCP Cloud Logging integration."""

from __future__ import annotations

import functools
import inspect
import json
import logging
import sys
import time
from datetime import datetime, timezone


class GCPJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON compatible with GCP Cloud Logging."""

    EXTRA_FIELDS = ("tool", "arguments", "duration_ms", "success", "error")

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "logger": record.name,
        }
        for key in self.EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value
        if record.exc_info and record.exc_info[1]:
            log_entry["error"] = str(record.exc_info[1])
            log_entry["severity"] = "ERROR"
        return json.dumps(log_entry, default=str)


def _sanitize_args(fn, args, kwargs) -> dict:
    """Build a dict of argument names to values, excluding the Context parameter."""
    sig = inspect.signature(fn)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    return {k: v for k, v in bound.arguments.items() if k != "ctx"}


logger = logging.getLogger("climate_impacts_mcp.tools")


def log_tool_call(fn):
    """Decorator that logs tool call name, arguments, duration, and success/failure."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        tool_name = fn.__name__
        try:
            sanitized = _sanitize_args(fn, args, kwargs)
        except Exception:
            sanitized = {}

        start = time.monotonic()
        try:
            result = await fn(*args, **kwargs)
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            logger.info(
                "Tool call completed",
                extra={
                    "tool": tool_name,
                    "arguments": sanitized,
                    "duration_ms": duration_ms,
                    "success": True,
                },
            )
            return result
        except Exception as exc:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            logger.error(
                "Tool call failed",
                extra={
                    "tool": tool_name,
                    "arguments": sanitized,
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": str(exc),
                },
            )
            raise

    return wrapper


def setup_logging() -> None:
    """Configure structured JSON logging to stdout for GCP Cloud Logging."""
    root_logger = logging.getLogger("climate_impacts_mcp")
    if root_logger.handlers:
        return  # Already configured
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(GCPJsonFormatter())
    root_logger.addHandler(handler)
    root_logger.propagate = False
