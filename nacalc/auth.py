"""Session-based per-user auth. Passwords hashed with stdlib scrypt."""
import base64
import hashlib
import hmac
import os
from functools import wraps

from flask import session, redirect, url_for, request, abort

from . import store, config

_N, _R, _P = 2 ** 14, 8, 1
_MAXMEM = 80 * 1024 * 1024


def _b64(b):
    return base64.b64encode(b).decode()


def hash_password(pw):
    salt = os.urandom(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32, maxmem=_MAXMEM)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(dk)}"


def verify_password(pw, stored):
    try:
        algo, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.scrypt(pw.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                            dklen=len(expected), maxmem=_MAXMEM)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def current_user():
    uid = session.get("uid")
    return store.get_user(uid) if uid else None


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("uid"):
            return redirect(url_for("nacalc.login", next=request.path))
        return f(*a, **k)
    return w


def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        u = current_user()
        if not u:
            return redirect(url_for("nacalc.login", next=request.path))
        if not u["is_admin"]:
            abort(403)
        return f(*a, **k)
    return w


def bootstrap_admin():
    """Create the first admin from env vars if there are no users yet."""
    if store.count_users() == 0 and config.BOOTSTRAP_ADMIN_EMAIL and config.BOOTSTRAP_ADMIN_PASSWORD:
        store.create_user(config.BOOTSTRAP_ADMIN_EMAIL, "Beheerder",
                          hash_password(config.BOOTSTRAP_ADMIN_PASSWORD), is_admin=1)
