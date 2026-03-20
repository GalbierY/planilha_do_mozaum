from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass


_ITERATIONS = 200_000


@dataclass(frozen=True)
class PasswordHash:
    salt_hex: str
    hash_hex: str


def hash_password(password: str, *, salt: bytes | None = None) -> PasswordHash:
    if salt is None:
        salt = os.urandom(16)
    pw = (password or "").encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", pw, salt, _ITERATIONS, dklen=32)
    return PasswordHash(salt_hex=salt.hex(), hash_hex=dk.hex())


def verify_password(password: str, *, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    pw = (password or "").encode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", pw, salt, _ITERATIONS, dklen=32)
    return secrets.compare_digest(dk, expected)
