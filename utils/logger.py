import logging
import logging.config
import os
import glob
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler

LOG_DIR_GENERAL = "logs/general"
LOG_DIR_ERRORS = "logs/errors"

os.makedirs(LOG_DIR_GENERAL, exist_ok=True)
os.makedirs(LOG_DIR_ERRORS, exist_ok=True)


class ErrorLogFilter(logging.Filter):
    def filter(self, record):
        return record.levelname in ("ERROR", "CRITICAL")


def clean_old_logs(log_dir, days=30):
    now = datetime.now()
    for file in glob.glob(os.path.join(log_dir, "*.txt")):
        file_time = datetime.fromtimestamp(os.path.getmtime(file))
        if now - file_time > timedelta(days=days):
            os.remove(file)


class DailyRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, log_dir, filename, **kwargs):
        self.log_dir = log_dir
        full_path = os.path.join(log_dir, filename)
        super().__init__(
            full_path,
            when="midnight",
            interval=1,
            backupCount=0,
            encoding="utf-8",
            **kwargs,
        )

    def doRollover(self):
        super().doRollover()
        clean_old_logs(self.log_dir, days=30)


def get_log_filename(prefix):
    return f"{prefix}_{datetime.now().strftime('%Y-%m-%d')}.txt"


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(filename)s:%(lineno)d #%(levelname)-8s"
            "[%(asctime)s] - %(name)s - %(message)s"
        },
    },
    "filters": {
        "error_filter": {
            "()": ErrorLogFilter,
        }
    },
    "handlers": {
        "file": {
            "()": DailyRotatingFileHandler,
            "log_dir": LOG_DIR_GENERAL,
            "filename": get_log_filename("app_log"),
            "level": "INFO",
            "formatter": "default",
        },
        "error_file": {
            "()": DailyRotatingFileHandler,
            "log_dir": LOG_DIR_ERRORS,
            "filename": get_log_filename("error_log"),
            "level": "ERROR",
            "formatter": "default",
            "filters": ["error_filter"],
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
        },
    },
    "root": {"level": "INFO", "handlers": ["file", "error_file", "console"]},
}
