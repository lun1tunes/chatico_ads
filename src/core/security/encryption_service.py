from __future__ import annotations

from cryptography.fernet import Fernet

from ..config import settings


class EncryptionService:
    def __init__(self, key: str | None = None) -> None:
        self._fernet = Fernet((key or settings.field_encryption_key).encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
