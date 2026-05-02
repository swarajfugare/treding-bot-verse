from typing import Optional, Tuple

from backend.database import DB_LOCK, dict_row, get_connection, now_iso
from backend.utils.crypto import decrypt_value, encrypt_value, mask_value


def normalize_credentials(payload: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    api_key = payload.get("api_key") or payload.get("key")
    api_secret = payload.get("api_secret") or payload.get("secret")
    if not isinstance(api_key, str) or not api_key.strip():
        return None, None, "API key is required."
    if not isinstance(api_secret, str) or not api_secret.strip():
        return None, None, "API secret is required."
    return api_key.strip(), api_secret.strip(), None


def save_credentials(api_key: str, api_secret: str) -> dict:
    encrypted_key = encrypt_value(api_key)
    encrypted_secret = encrypt_value(api_secret)
    timestamp = now_iso()
    with DB_LOCK, get_connection() as conn:
        conn.execute(
            """
            INSERT INTO credentials (id, api_key_encrypted, api_secret_encrypted, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                api_key_encrypted = excluded.api_key_encrypted,
                api_secret_encrypted = excluded.api_secret_encrypted,
                updated_at = excluded.updated_at
            """,
            (encrypted_key, encrypted_secret, timestamp),
        )
        conn.commit()
    return {
        "success": True,
        "connected": True,
        "api_key": mask_value(api_key),
        "api_secret": mask_value(api_secret),
        "updated_at": timestamp,
        "error": None,
    }


def get_credentials(masked: bool = True) -> dict:
    with DB_LOCK, get_connection() as conn:
        row = conn.execute("SELECT * FROM credentials WHERE id = 1").fetchone()
    item = dict_row(row)
    if not item:
        return {"success": True, "connected": False, "api_key": None, "api_secret": None, "updated_at": None, "error": None}

    api_key = decrypt_value(item["api_key_encrypted"])
    api_secret = decrypt_value(item["api_secret_encrypted"])
    if api_key is None or api_secret is None:
        return {
            "success": False,
            "connected": False,
            "api_key": None,
            "api_secret": None,
            "updated_at": item["updated_at"],
            "error": "Saved credentials could not be decrypted with the current Fernet key.",
        }

    return {
        "success": True,
        "connected": True,
        "api_key": mask_value(api_key) if masked else api_key,
        "api_secret": mask_value(api_secret) if masked else api_secret,
        "updated_at": item["updated_at"],
        "error": None,
    }


def test_credentials(payload: dict) -> dict:
    api_key, api_secret, error = normalize_credentials(payload)
    if error:
        saved = get_credentials(masked=False)
        if not saved.get("connected"):
            return {"success": False, "connected": False, "error": error}
        api_key = saved["api_key"]
        api_secret = saved["api_secret"]

    if len(api_key.strip()) < 6 or len(api_secret.strip()) < 6:
        return {"success": False, "connected": False, "message": "Credentials are too short.", "error": "Credentials are too short to be valid API credentials."}

    from backend.services.exchange_service import test_connection

    result = test_connection()
    if result.get("success"):
        return {"success": True, "connected": True, "message": "Connected", "error": None}
    return {
        "success": False,
        "connected": False,
        "message": result.get("message") or result.get("error") or "Connection failed",
        "error": result.get("error") or "Connection failed",
    }
