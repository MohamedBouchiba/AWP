"""Local smoke test — no Teamleader, no real DB.

Boots the Flask app against an isolated temp DATA_DIR with sync disabled, then
hits every page and asserts it returns the expected status with CSS present.
Run after any change (especially CSS): `python scripts/smoke_test.py`.
"""
import os
import sys
import shutil
import tempfile

# Must be set BEFORE importing app (read at import time).
os.environ["NACALC_DISABLE_SYNC"] = "1"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="nacalc_smoke_")
os.environ.setdefault("SECRET_KEY", "smoke-test-key")

# Make the repo root importable when run as `python scripts/smoke_test.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as appmod          # noqa: E402
from nacalc import store, auth  # noqa: E402

flask_app = appmod.app
flask_app.config["TESTING"] = True

EMAIL = "smoke@test.local"
if not store.get_user_by_email(EMAIL):
    store.create_user(EMAIL, "Smoke", auth.hash_password("x"), is_admin=1)
uid = store.get_user_by_email(EMAIL)["id"]

client = flask_app.test_client()
failures = []


def check(path, expect=200, needs_style=True, login=False):
    with client.session_transaction() as s:
        if login:
            s["uid"] = uid
        else:
            s.pop("uid", None)
    r = client.get(path)
    body = r.get_data(as_text=True)
    ok = r.status_code == expect
    if ok and needs_style and expect == 200 and "<style>" not in body:
        ok = False
    print(f"{'OK  ' if ok else 'FAIL'} {path:20s} -> {r.status_code}"
          f"{'' if ok else f' (expected {expect})'}")
    if not ok:
        failures.append(path)


# Public pages
check("/healthz", 200, needs_style=False)
check("/", 200)                       # onboarding wizard
check("/app/login", 200)              # dashboard login
# Protected page while logged out -> redirect to login
check("/app", 302, needs_style=False, login=False)
# Logged-in dashboard pages
for p in ["/app", "/app/overzicht", "/app/analyse", "/app/meldingen", "/app/beheer"]:
    check(p, 200, login=True)

shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)

if failures:
    print("\nSMOKE TEST FAILED:", failures)
    sys.exit(1)
print("\nAll smoke checks passed.")
