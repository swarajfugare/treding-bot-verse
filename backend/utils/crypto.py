import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def _persist_generated_key(generated: str) -> None:
    try:
        if ENV_PATH.exists():
            lines = ENV_PATH.read_text().splitlines()
            replaced = False
            updated = []
            for line in lines:
                if line.startswith("FERNET_KEY="):
                    updated.append(f"FERNET_KEY={generated}")
                    replaced = True
                else:
                    updated.append(line)
            if not replaced:
                updated.append(f"FERNET_KEY={generated}")
            ENV_PATH.write_text("\n".join(updated) + "\n")
        else:
            ENV_PATH.write_text(f"FERNET_KEY={generated}\n")
    except OSError:
        print("Could not persist generated FERNET_KEY to backend/.env.")


def _build_fernet() -> Fernet:
    configured_key = os.getenv("FERNET_KEY", "").strip()
    if configured_key:
        try:
            return Fernet(configured_key.encode())
        except Exception:
            generated = Fernet.generate_key().decode()
            print("Invalid FERNET_KEY found. Using generated key for this session:")
            print(generated)
            return Fernet(generated.encode())

    generated = Fernet.generate_key().decode()
    _persist_generated_key(generated)
    print("FERNET_KEY missing. Generated and saved a key to backend/.env:")
    print(generated)
    return Fernet(generated.encode())


FERNET = _build_fernet()


def encrypt_value(value: str) -> str:
    return FERNET.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> Optional[str]:
    try:
        return FERNET.decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def mask_value(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}****{value[-2:]}"
