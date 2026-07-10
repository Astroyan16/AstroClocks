"""Runtime logging helpers for AstroClocks."""

from __future__ import annotations

import logging
import os
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "astroclocks"
LOG_FILE_NAME = "astroclocks.log"
DEFAULT_LOG_MAX_BYTES = 512 * 1024
DEFAULT_LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

_BASE_LOGGER = logging.getLogger(LOGGER_NAME)
if not _BASE_LOGGER.handlers:
    _BASE_LOGGER.addHandler(logging.NullHandler())
_BASE_LOGGER.propagate = False


def default_log_directory():
    override = str(os.environ.get("ASTROCLOCKS_LOG_DIR") or "").strip()
    if override:
        return Path(override).expanduser()

    local_app_data = str(os.environ.get("LOCALAPPDATA") or "").strip()
    if local_app_data:
        return Path(local_app_data) / "AstroClocks" / "logs"

    return Path.home() / ".astroclocks" / "logs"


def default_log_path(log_dir=None):
    return Path(log_dir or default_log_directory()) / LOG_FILE_NAME


def get_logger(name=None):
    if not name:
        return logging.getLogger(LOGGER_NAME)

    module_name = str(name)
    if module_name.startswith(f"{LOGGER_NAME}."):
        return logging.getLogger(module_name)
    if module_name == LOGGER_NAME:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{module_name}")


def _runtime_handler(logger):
    for handler in logger.handlers:
        if getattr(handler, "_astroclocks_runtime_handler", False):
            return handler
    return None


def configure_runtime_logging(
    log_dir=None,
    max_bytes=DEFAULT_LOG_MAX_BYTES,
    backup_count=DEFAULT_LOG_BACKUP_COUNT,
):
    logger = get_logger()
    log_path = default_log_path(log_dir)
    current_handler = _runtime_handler(logger)
    current_path = Path(getattr(current_handler, "baseFilename", "")) if current_handler else None
    if current_handler is not None and current_path == log_path:
        return log_path

    if current_handler is not None:
        logger.removeHandler(current_handler)
        current_handler.close()

    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler._astroclocks_runtime_handler = True
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.info("Runtime logging initialised: %s", log_path)
    return log_path


def flush_runtime_logs():
    logger = get_logger()
    handler = _runtime_handler(logger)
    if handler is not None:
        handler.flush()


def close_runtime_logging():
    logger = get_logger()
    handler = _runtime_handler(logger)
    if handler is not None:
        logger.removeHandler(handler)
        handler.close()


def log_exception(logger, message, exc):
    logger.error(message, exc_info=(type(exc), exc, exc.__traceback__))


def install_global_exception_hooks(root=None):
    logger = get_logger("runtime")

    if getattr(sys.excepthook, "_astroclocks_runtime_hook", None) != "sys":
        previous_sys_hook = sys.excepthook

        def _sys_excepthook(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                return previous_sys_hook(exc_type, exc_value, exc_traceback)
            logger.critical(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
            previous_sys_hook(exc_type, exc_value, exc_traceback)

        _sys_excepthook._astroclocks_runtime_hook = "sys"
        sys.excepthook = _sys_excepthook

    thread_hook = getattr(threading, "excepthook", None)
    if thread_hook is not None and getattr(thread_hook, "_astroclocks_runtime_hook", None) != "thread":
        previous_thread_hook = thread_hook

        def _thread_excepthook(args):
            if args.exc_type is not SystemExit:
                thread_name = getattr(getattr(args, "thread", None), "name", "unknown")
                logger.error(
                    "Unhandled exception in thread %s",
                    thread_name,
                    exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
                )
            previous_thread_hook(args)

        _thread_excepthook._astroclocks_runtime_hook = "thread"
        threading.excepthook = _thread_excepthook

    if root is None:
        return

    callback_hook = getattr(root, "report_callback_exception", None)
    if getattr(callback_hook, "_astroclocks_runtime_hook", None) == "tk":
        return

    previous_callback_hook = callback_hook

    def _tk_callback_exception(exc_type, exc_value, exc_traceback):
        logger.error(
            "Unhandled Tk callback exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        if callable(previous_callback_hook):
            try:
                previous_callback_hook(exc_type, exc_value, exc_traceback)
                return
            except Exception as hook_exc:
                logger.error(
                    "Tk exception fallback handler failed",
                    exc_info=(type(hook_exc), hook_exc, hook_exc.__traceback__),
                )
        traceback.print_exception(exc_type, exc_value, exc_traceback)

    _tk_callback_exception._astroclocks_runtime_hook = "tk"
    root.report_callback_exception = _tk_callback_exception
