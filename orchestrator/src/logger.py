"""Structured JSON logger for the Codex Dev Team Orchestrator."""

import structlog


def _rename_event_to_message(_, __, event_dict):
    """Rename structlog's 'event' key to 'message' for consistency."""
    event_dict["message"] = event_dict.pop("event", "")
    return event_dict


def _rename_log_level(_, __, event_dict):
    """Rename structlog's 'log_level' key to 'level' (uppercased)."""
    event_dict["level"] = event_dict.pop("log_level", "INFO").upper()
    return event_dict


structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        _rename_log_level,
        _rename_event_to_message,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    logger_factory=structlog.PrintLoggerFactory(),
)

_log = structlog.get_logger()

info = _log.info
warning = _log.warning
error = _log.error
debug = _log.debug
