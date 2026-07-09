import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astroclocks import secure_store


class SecureStoreTests(unittest.TestCase):
    def test_normalize_application_id_accepts_raw_or_authorization_header(self):
        self.assertEqual(secure_store._normalize_application_id("abc123"), "abc123")
        self.assertEqual(secure_store._normalize_application_id("Basic abc123"), "abc123")
        self.assertEqual(secure_store._normalize_application_id("Bearer abc123"), "abc123")
        self.assertEqual(
            secure_store._normalize_application_id("Authorization: Basic abc123"),
            "abc123",
        )

    def test_save_load_and_delete_meteofrance_application_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret.dpapi"
            with patch(
                "astroclocks.secure_store.protect_text",
                side_effect=lambda value: f"protected:{value}",
            ):
                secure_store.save_meteofrance_application_id("Basic abc123", path=path)

            with patch(
                "astroclocks.secure_store.unprotect_text",
                side_effect=lambda value: value.removeprefix("protected:"),
            ):
                self.assertEqual(
                    secure_store.load_meteofrance_application_id(path=path),
                    "abc123",
                )
                self.assertTrue(secure_store.has_meteofrance_application_id(path=path))

            secure_store.delete_meteofrance_application_id(path=path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
