import os
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from astroclocks import runtime_logging


class _FakeRoot:
    def __init__(self):
        self.calls = []

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        self.calls.append((exc_type, exc_value, exc_traceback))


class RuntimeLoggingTests(unittest.TestCase):
    def setUp(self):
        self._previous_sys_excepthook = sys.excepthook
        self._previous_thread_excepthook = threading.excepthook
        self._previous_log_dir = os.environ.get("ASTROCLOCKS_LOG_DIR")

    def tearDown(self):
        sys.excepthook = self._previous_sys_excepthook
        threading.excepthook = self._previous_thread_excepthook
        runtime_logging.close_runtime_logging()
        if self._previous_log_dir is None:
            os.environ.pop("ASTROCLOCKS_LOG_DIR", None)
        else:
            os.environ["ASTROCLOCKS_LOG_DIR"] = self._previous_log_dir

    def test_configure_runtime_logging_writes_log_file_in_override_directory(self):
        with TemporaryDirectory() as temp_dir:
            os.environ["ASTROCLOCKS_LOG_DIR"] = temp_dir

            log_path = runtime_logging.configure_runtime_logging()
            runtime_logging.get_logger("tests").info("hello from test")
            runtime_logging.flush_runtime_logs()

            self.assertEqual(log_path, Path(temp_dir) / "astroclocks.log")
            self.assertTrue(log_path.exists())
            self.assertIn("hello from test", log_path.read_text(encoding="utf-8"))
            runtime_logging.close_runtime_logging()

    def test_install_global_exception_hooks_wraps_tk_callback_exceptions(self):
        with TemporaryDirectory() as temp_dir:
            log_path = runtime_logging.configure_runtime_logging(log_dir=temp_dir)
            root = _FakeRoot()

            runtime_logging.install_global_exception_hooks(root)

            try:
                raise ValueError("boom")
            except ValueError as exc:
                root.report_callback_exception(type(exc), exc, exc.__traceback__)

            runtime_logging.flush_runtime_logs()

            self.assertEqual(len(root.calls), 1)
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("Unhandled Tk callback exception", content)
            self.assertIn("ValueError: boom", content)
            runtime_logging.close_runtime_logging()

    def test_install_global_exception_hooks_wraps_thread_exceptions(self):
        with TemporaryDirectory() as temp_dir:
            log_path = runtime_logging.configure_runtime_logging(log_dir=temp_dir)
            threading.excepthook = lambda args: None

            runtime_logging.install_global_exception_hooks()

            try:
                raise RuntimeError("thread failure")
            except RuntimeError as exc:
                args = SimpleNamespace(
                    exc_type=type(exc),
                    exc_value=exc,
                    exc_traceback=exc.__traceback__,
                    thread=SimpleNamespace(name="TestThread"),
                )
                threading.excepthook(args)

            runtime_logging.flush_runtime_logs()

            content = log_path.read_text(encoding="utf-8")
            self.assertIn("Unhandled exception in thread TestThread", content)
            self.assertIn("RuntimeError: thread failure", content)
            runtime_logging.close_runtime_logging()


if __name__ == "__main__":
    unittest.main()
