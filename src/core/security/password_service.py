from __future__ import annotations

from pwdlib import PasswordHash


class PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self._hasher.verify(password, password_hash)
