"""v2.5.3.2 — the pipeline (Python) decrypts what the app (TS) encrypts, and vice versa.

Proves byte-compatibility of the two AES-256-GCM implementations using a throwaway key — no
live DB, no real secret. Needs the frontend tsx binary. Plain asserts:
    python tests/test_vault_crossimpl.py
"""
import base64
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vault import decrypt_secret, encrypt_secret, load_master_key  # noqa: E402

_FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
_TSX = os.path.join("node_modules", ".bin", "tsx")

key = os.urandom(32)
kb64 = base64.b64encode(key).decode()
env = {**os.environ, "CREDENTIAL_VAULT_KEY": kb64}
plaintext = "espn_s2=AEB1a2b3verylongcookievalue; SWID={1234-ABCD-5678}"


def _tsx(mode: str, data: str) -> str:
    p = subprocess.run([_TSX, "scripts/vault-cli.ts", mode], input=data,
                       capture_output=True, text=True, cwd=_FRONTEND, env=env, timeout=60)
    assert p.returncode == 0, p.stderr
    return p.stdout


# load_master_key parity
assert load_master_key(env) == key
assert load_master_key({}) is None

# direction 1: TS encrypts → Python decrypts (the real pipeline path)
ts_packed = _tsx("encrypt", plaintext)
assert ts_packed.count(".") == 2, ts_packed
assert decrypt_secret(ts_packed, key) == plaintext, "python must decrypt TS-encrypted secret"

# direction 2: Python encrypts → TS decrypts (symmetry)
py_packed = encrypt_secret(plaintext, key)
assert _tsx("decrypt", py_packed) == plaintext, "TS must decrypt python-encrypted secret"

# tamper is rejected cross-impl too
iv, tag, ct = ts_packed.split(".")
ctb = bytearray(base64.b64decode(ct))
ctb[-1] ^= 0x01
tampered = ".".join([iv, tag, base64.b64encode(bytes(ctb)).decode()])
try:
    decrypt_secret(tampered, key)
    raise AssertionError("tampered ciphertext must not decrypt")
except Exception as e:  # noqa: BLE001
    assert "AssertionError" not in type(e).__name__, e

print("ok test_vault_crossimpl")
