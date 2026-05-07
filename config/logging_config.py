"""Loguru-based structured logging configuration.

Logs are written to two separate files:
- server.log: Clean debugging log (truncated on startup)
- audit.log: Persistent audit trail (rotated, compressed, retained for 30 days)

Stdlib logging is intercepted and funneled to loguru.
Context vars (request_id, node_id, chat_id) from contextualize() are
included at top level for easy grep/filter.
"""

import json
import logging
import re
from pathlib import Path

from loguru import logger

_configured = False

# Context keys we promote to top-level JSON for traceability
_CONTEXT_KEYS = ("request_id", "node_id", "chat_id")

_TELEGRAM_BOT_RE = re.compile(
    r"(https?://api\.telegram\.org/)bot([0-9]+:[A-Za-z0-9_-]+)(/?)",
    re.IGNORECASE,
)
# Authorization: Bearer <token> (HTTP client / proxy debug lines)
_AUTH_BEARER_RE = re.compile(
    r"(\bAuthorization\s*:\s*Bearer\s+)([^\s'\"]+)",
    re.IGNORECASE,
)


def _redact_sensitive_substrings(message: str) -> str:
    """Remove obvious API tokens and secrets before JSON log line emission."""
    text = _TELEGRAM_BOT_RE.sub(r"\1bot<redacted>\3", message)
    return _AUTH_BEARER_RE.sub(r"\1<redacted>", text)


def _serialize_with_context(record) -> str:
    """Format record as JSON with context vars at top level.
    Returns a format template; we inject _json into record for output.
    """
    extra = record.get("extra", {})
    out = {
        "time": str(record["time"]),
        "level": record["level"].name,
        "message": _redact_sensitive_substrings(str(record["message"])),
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    for key in _CONTEXT_KEYS:
        if key in extra and extra[key] is not None:
            out[key] = extra[key]
    record["_json"] = json.dumps(out, default=str)
    return "{_json}\n"


class InterceptHandler(logging.Handler):
    """Redirect stdlib logging to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(
    log_file: str,
    *,
    force: bool = False,
    verbose_third_party: bool = False,
    truncate_on_start: bool = True,
) -> None:
    """Configure loguru with JSON output to log_file and intercept stdlib logging.

    Idempotent: skips if already configured (e.g. hot reload).
    Use force=True to reconfigure (e.g. in tests with a different log path).

    When ``verbose_third_party`` is false, noisy HTTP and Telegram loggers are capped
    at WARNING unless explicitly configured otherwise.

    When ``truncate_on_start`` is True (default for clean debugging), the log file
    is truncated on fresh start. Set to False for persistent audit trails.
    """
    global _configured
    if _configured and not force:
        return
    _configured = True

    # Remove default loguru handler (writes to stderr)
    logger.remove()

    # Truncate log file on fresh start for clean debugging (default behavior)
    # Set truncate_on_start=False to preserve logs for audit trail
    if truncate_on_start:
        Path(log_file).write_text("")

    # Add file sink: JSON lines, DEBUG level, context vars at top level
    # Configure rotation with retention for long-term logging
    logger.add(
        log_file,
        level="DEBUG",
        format=_serialize_with_context,
        encoding="utf-8",
        mode="a",
        rotation="50 MB",
        retention="30 days",  # Keep 30 days of logs
        compression="zip",  # Compress rotated logs
    )

    # Intercept stdlib logging: route all root logger output to loguru
    intercept = InterceptHandler()
    logging.root.handlers = [intercept]
    logging.root.setLevel(logging.DEBUG)

    third_party = (
        "httpx",
        "httpcore",
        "httpcore.http11",
        "httpcore.connection",
        "telegram",
        "telegram.ext",
    )
    for name in third_party:
        logging.getLogger(name).setLevel(
            logging.WARNING if not verbose_third_party else logging.NOTSET
        )
