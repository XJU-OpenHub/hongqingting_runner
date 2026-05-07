"""
sk-xxx-token vault for hongqingting_runner.

Each token IS the encryption key (derived via SHA-256 → Fernet base64 key).
The vault on disk stores `{sha256(idx:sk)[:32]: {ciphertext, label, created_at}}`,
so possession of the file alone does not reveal any plaintext: an attacker would
need the original sk to derive the Fernet key.

CLI:
    python -m vault add [LABEL]      # plaintext on stdin → prints sk-xxx
    python -m vault list             # truncated view of every entry
    python -m vault delete SK        # revoke a token
    python -m vault decrypt SK       # smoke-test: decrypts and prints config
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

VAULT_PATH = Path(os.environ.get(
    "HONGQINGTING_VAULT",
    "/opt/hongqingting_runner/secrets/vault.json",
))


# ---------- token helpers ----------

def make_token() -> str:
    return "sk-" + secrets.token_urlsafe(32)


def _derive_key(sk: str) -> bytes:
    """Fernet keys are 32 bytes urlsafe-base64. SHA-256 of the token is exactly
    32 bytes, so we can wrap it directly without HKDF."""
    digest = hashlib.sha256(sk.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _index(sk: str) -> str:
    """A separate hash so the vault file index can't be brute-forced into the
    encryption key — uses a different prefix than _derive_key."""
    return hashlib.sha256(("idx::" + sk).encode("utf-8")).hexdigest()[:32]


# ---------- vault file ----------

def _ensure_dir():
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(VAULT_PATH.parent, 0o700)
    except PermissionError:
        pass


def load_vault() -> dict:
    if not VAULT_PATH.exists():
        return {}
    with open(VAULT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_vault(v: dict):
    _ensure_dir()
    tmp = VAULT_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    tmp.replace(VAULT_PATH)
    os.chmod(VAULT_PATH, 0o600)


# ---------- public API ----------

def add(plaintext: str, label: str = "") -> str:
    sk = make_token()
    f = Fernet(_derive_key(sk))
    ct = f.encrypt(plaintext.encode("utf-8")).decode("ascii")
    vault = load_vault()
    vault[_index(sk)] = {
        "ciphertext": ct,
        "label": label,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    save_vault(vault)
    return sk


def decrypt(sk: str) -> str:
    vault = load_vault()
    entry = vault.get(_index(sk))
    if not entry:
        raise KeyError("token not found")
    try:
        return Fernet(_derive_key(sk)).decrypt(
            entry["ciphertext"].encode("ascii")
        ).decode("utf-8")
    except InvalidToken as exc:
        raise KeyError("token does not match this entry") from exc


def remove(sk: str) -> bool:
    vault = load_vault()
    idx = _index(sk)
    if idx not in vault:
        return False
    del vault[idx]
    save_vault(vault)
    return True


# ---------- CLI ----------

def _cli():
    args = sys.argv[1:]
    if not args:
        print("usage: vault add|list|delete|decrypt", file=sys.stderr)
        sys.exit(2)
    cmd = args[0]
    if cmd == "add":
        label = args[1] if len(args) > 1 else ""
        plain = sys.stdin.read()
        if not plain.strip():
            print("error: pipe plaintext on stdin", file=sys.stderr)
            sys.exit(1)
        sk = add(plain, label=label)
        print(sk)
    elif cmd == "list":
        v = load_vault()
        if not v:
            print("(empty)")
            return
        for idx, entry in v.items():
            print(f"{idx}  {entry.get('created_at',''):<20}  {entry.get('label','')}")
    elif cmd == "delete":
        if len(args) < 2:
            print("usage: vault delete SK", file=sys.stderr); sys.exit(2)
        ok = remove(args[1])
        print("deleted" if ok else "not found")
    elif cmd == "decrypt":
        if len(args) < 2:
            print("usage: vault decrypt SK", file=sys.stderr); sys.exit(2)
        try:
            print(decrypt(args[1]))
        except KeyError as e:
            print(f"error: {e}", file=sys.stderr); sys.exit(1)
    else:
        print(f"unknown command: {cmd}", file=sys.stderr); sys.exit(2)


if __name__ == "__main__":
    _cli()
