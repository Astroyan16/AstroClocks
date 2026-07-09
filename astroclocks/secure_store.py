"""Small Windows DPAPI-backed secret store for local AstroClocks credentials."""

import base64
from pathlib import Path

from astroclocks.settings import SETTINGS_FILE


SECRET_DIR = SETTINGS_FILE.parent
METEOFRANCE_APPLICATION_ID_FILE = SECRET_DIR / "MeteoFranceApplicationId.dpapi"


class SecureStoreUnavailable(RuntimeError):
    """Raised when the platform cannot protect local secrets."""


def _load_win32crypt():
    try:
        import win32crypt  # type: ignore
    except ImportError as exc:
        raise SecureStoreUnavailable(
            "Windows DPAPI requires pywin32/win32crypt."
        ) from exc
    return win32crypt


def _normalize_application_id(value):
    text = str(value or "").strip()
    if not text:
        return ""
    lower_text = text.lower()
    if lower_text.startswith("authorization:"):
        text = text.split(":", 1)[1].strip()
        lower_text = text.lower()
    if lower_text.startswith("basic ") or lower_text.startswith("bearer "):
        text = text.split(None, 1)[1].strip()
    return text


def protect_text(value):
    text = str(value or "")
    win32crypt = _load_win32crypt()
    protected = win32crypt.CryptProtectData(
        text.encode("utf-8"),
        "AstroClocks",
        None,
        None,
        None,
        0,
    )
    return base64.b64encode(protected).decode("ascii")


def unprotect_text(value):
    win32crypt = _load_win32crypt()
    encrypted = base64.b64decode(str(value).encode("ascii"))
    _description, payload = win32crypt.CryptUnprotectData(
        encrypted,
        None,
        None,
        None,
        0,
    )
    return payload.decode("utf-8")


def save_meteofrance_application_id(value, path=METEOFRANCE_APPLICATION_ID_FILE):
    application_id = _normalize_application_id(value)
    if not application_id:
        raise ValueError("Météo-France API key is empty.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(protect_text(application_id), encoding="ascii")


def load_meteofrance_application_id(path=METEOFRANCE_APPLICATION_ID_FILE):
    path = Path(path)
    try:
        payload = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return ""
    if not payload:
        return ""
    return unprotect_text(payload)


def delete_meteofrance_application_id(path=METEOFRANCE_APPLICATION_ID_FILE):
    path = Path(path)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def has_meteofrance_application_id(path=METEOFRANCE_APPLICATION_ID_FILE):
    return bool(load_meteofrance_application_id(path=path))
