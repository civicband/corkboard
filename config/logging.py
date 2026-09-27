"""Structured JSON logging helpers for the corkboard Django app."""

from pythonjsonlogger.json import JsonFormatter

# Record attributes that add noise when merged into the JSON payload.
_NOISY_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "levelname",
        "levelno",
        "msecs",
        "msg",
        "relativeCreated",
        "stack_info",
        "taskName",
    }
)


class CorkboardJsonFormatter(JsonFormatter):
    """JSON formatter that lifts every useful LogRecord attribute to the top level.

    Standard metadata (logger name, level, source location, process/thread) is
    emitted as top-level keys, extras passed via ``Logger.extra={...}`` are merged
    in as-is, and ``level``/``timestamp``/``traceback`` are normalized so logs are
    easy to query in VictoriaLogs.
    """

    _FORMAT = (
        "%(name)s %(levelname)s %(module)s %(funcName)s %(lineno)s "
        "%(process)s %(processName)s %(thread)s %(threadName)s "
        "%(pathname)s %(message)s"
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("reserved_attrs", [])
        kwargs.setdefault(
            "rename_fields",
            {
                "funcName": "function",
                "lineno": "line",
                "processName": "process_name",
                "threadName": "thread_name",
            },
        )
        kwargs.setdefault("timestamp", True)
        super().__init__(*args or (self._FORMAT,), **kwargs)

    def add_fields(self, log_data, record, message_dict):
        super().add_fields(log_data, record, message_dict)
        if "levelname" in log_data:
            log_data["level"] = log_data.pop("levelname").lower()
        for key in _NOISY_ATTRS:
            log_data.pop(key, None)
        if record.exc_info and record.exc_info[0] is not None:
            log_data["traceback"] = self.formatException(record.exc_info)
