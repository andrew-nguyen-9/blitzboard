"""Pipeline-side credential-vault crypto (v2.5.3.2).

Byte-compatible with the TS implementation in frontend/lib/crypto/vault.ts: app-layer
AES-256-GCM, payload "iv.tag.ciphertext" (each base64), 32-byte master key from
CREDENTIAL_VAULT_KEY (base64). The pipeline reads ciphertext from credential_vault with the
service-role key and decrypts transiently to call ESPN/Sleeper — plaintext never persists.
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_IV_LEN = 12
_KEY_LEN = 32


def load_master_key(env: dict | None = None) -> bytes | None:
    """Load + validate the master key from env. None when unset (offline-safe)."""
    env = os.environ if env is None else env
    b64 = env.get("CREDENTIAL_VAULT_KEY")
    if not b64:
        return None
    key = base64.b64decode(b64)
    if len(key) != _KEY_LEN:
        raise ValueError(f"CREDENTIAL_VAULT_KEY must decode to {_KEY_LEN} bytes (got {len(key)})")
    return key


def decrypt_secret(packed: str, key: bytes) -> str:
    """Decrypt "iv.tag.ciphertext" → plaintext. Raises on tamper/wrong key/malformed input."""
    parts = packed.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError("malformed ciphertext")
    iv, tag, ct = (base64.b64decode(p) for p in parts)
    # Node exposes the GCM tag separately; cryptography expects ciphertext || tag appended.
    return AESGCM(key).decrypt(iv, ct + tag, None).decode("utf-8")


def encrypt_secret(plaintext: str, key: bytes) -> str:
    """Encrypt plaintext → "iv.tag.ciphertext" (base64), random IV. Symmetric to the TS format."""
    iv = os.urandom(_IV_LEN)
    blob = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)  # ciphertext || tag
    ct, tag = blob[:-16], blob[-16:]
    return ".".join(base64.b64encode(b).decode() for b in (iv, tag, ct))
