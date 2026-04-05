import logging
import logging.config
import os
import sys

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "detailed",
            "encoding": "utf-8",
        },
    },

    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "graph": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "services": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "kb": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "core": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}


def _force_utf8_stdio():
    # Prevent cp1252 crashes when logs contain Vietnamese text on Windows terminals.
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass


def setup_logging():
    os.environ.setdefault("PYTHONUTF8", "1")
    _force_utf8_stdio()
    logging.config.dictConfig(LOGGING_CONFIG)