"""Golden-master fingerprint of every rendered page — the anti-regression anchor.

Renders each page against ONE deterministic fixture (the real A346 project, read
off production) and prints a SHA-256 per page. Run it BEFORE a change and AFTER:
any hash that moved must be a change you intended and can explain.

    python scripts/fingerprint.py > before.txt
    ...edit...
    python scripts/fingerprint.py > after.txt
    diff before.txt after.txt

Unlike the smoke test (which asserts pages still work), this catches *silent*
changes: a shifted number, a dropped column, a reordered bar.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile

os.environ["NACALC_DISABLE_SYNC"] = "1"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="nacalc_fp_")
os.environ.setdefault("SECRET_KEY", "fingerprint-key")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as appmod                              # noqa: E402
from nacalc import store, auth, calc, config      # noqa: E402

# Same nine phases as scripts/unit_test.py — the real A346, so the fingerprint
# is anchored on production data rather than on invented numbers.
A346_RAW = [
    {"name": "1. ADMINISTRATIE", "budget_eur": 249.90, "spent_eur": 120.00,
     "cost_eur": 100.00, "billed_eur": None, "tracked_hours": 1.33, "budget_hours": 2.93},
    {"name": "2. SCHETSONTWERP", "budget_eur": 5124.65, "spent_eur": 2401.25,
     "cost_eur": 1412.50, "billed_eur": None, "tracked_hours": 28.25, "budget_hours": 60.28},
    {"name": "3. VOORONTWERP", "budget_eur": 10245.90, "spent_eur": 13717.42,
     "cost_eur": 8994.73, "billed_eur": None, "tracked_hours": 158.91, "budget_hours": 120.53},
    {"name": "4. BOUWAANVRAAG", "budget_eur": 15620.45, "spent_eur": 10750.25,
     "cost_eur": 5876.25, "billed_eur": None, "tracked_hours": 126.40, "budget_hours": 183.77},
    {"name": "5. UITVOERINGSDOSSIER", "budget_eur": 9372.10, "spent_eur": 23485.21,
     "cost_eur": 14235.27, "billed_eur": None, "tracked_hours": 272.37, "budget_hours": 110.27},
    {"name": "6. COMPLETE WERFOPVOLGING", "budget_eur": 9372.10, "spent_eur": 6620.35,
     "cost_eur": 5810.71, "billed_eur": None, "tracked_hours": 77.48, "budget_hours": 110.27},
    {"name": "7. NAZORG", "budget_eur": 6247.50, "spent_eur": 0.0,
     "cost_eur": None, "billed_eur": None, "tracked_hours": 0.0, "budget_hours": 73.50},
    {"name": "8. MEERWERKEN", "budget_eur": 0.0, "spent_eur": 1380.68,
     "cost_eur": 1211.58, "billed_eur": None, "tracked_hours": 16.24, "budget_hours": 1.00},
    {"name": "9. BOUWCOORDINATIE", "budget_eur": 6247.50, "spent_eur": 345.00,
     "cost_eur": 287.50, "billed_eur": None, "tracked_hours": 3.83, "budget_hours": 73.50},
]

phases = calc.build_phases(A346_RAW, config.DEFAULT_THRESHOLDS)
summary = calc.project_summary(phases)
totals = calc.project_totals(phases)

store.upsert_snapshot({
    "project_id": "a346", "project_key": "A346",
    "titel": "A346 - Elsakkerweg Sint-Martens-Latem", "naam": "Elsakkerweg",
    "adres": "Elsakkerweg, Sint-Martens-Latem", "status": "open", "is_architectuur": 1,
    "categorie": "Nieuwbouw", "contracttype": "Vast", "verantw_arch": "WB",
    "verantw_medewerker": "", "budget_klant": None, "offerte_awp": 63860.78,
    "raming_vo": None, "uren_begroot": totals["begroot_uren_totaal"],
    "uren_gepresteerd": 684.82,
    "uren_begroot_gestart": totals["begroot_uren_aangesneden"],
    "uren_gepresteerd_gestart": totals["gepresteerd_uren"],
    "effectieve_kost": 37928.54, "gefactureerd": 11226.54,
    "project_type": "architectuur", "activity_json": json.dumps(["2026-07"]),
    "uren_per_persoon_json": json.dumps([{"uid": "u1", "hours": 684.8, "cost": None}]),
    "kost_bron": "teamleader",
    "marge": calc.margin(11226.54, 37928.54)[0],
    "marge_pct": calc.margin(11226.54, 37928.54)[1],
    "summary_status": summary["status"], "n_over": summary["n_over"],
    "n_warn": summary["n_warn"], "cost_estimated": 0, "werfbezoeken": 12,
    "besprekingen": 5, "attention_note": "5. UITVOERINGSDOSSIER",
    "phases_json": json.dumps(phases), "synced_at": "2026-08-12T00:00:00Z"})

store.set_config("tl_users", [{"id": "u1", "name": "Wim Bonami"}])
EMAIL = "fp@test.local"
if not store.get_user_by_email(EMAIL):
    store.create_user(EMAIL, "FP", auth.hash_password("x"), is_admin=1)
uid = store.get_user_by_email(EMAIL)["id"]

appmod.app.config["TESTING"] = True
client = appmod.app.test_client()
with client.session_transaction() as s:
    s["uid"] = uid

PAGES = [
    "/app",
    "/app/analyse",
    "/app/analyse?period=3",
    "/app/analyse2",
    "/app/meldingen",
    "/app/beheer",
    "/app/project/a346",
    "/app/login",
    "/",
]

print("A346 recalcule :")
print(f"  statut={summary['status']}  n_over={summary['n_over']}  n_warn={summary['n_warn']}")
print(f"  uren  gepresteerd={totals['gepresteerd_uren']}  "
      f"begroot_entames={totals['begroot_uren_aangesneden']}  "
      f"begroot_total={totals['begroot_uren_totaal']}")
for p in phases:
    print(f"  {p['naam']:<28} pct={str(p['pct']):>7}  {p['color']:<8} "
          f"started={int(p['started'])} applicable={int(p['applicable'])}")

print("\nEmpreintes des pages :")
for path in PAGES:
    r = client.get(path)
    body = r.get_data()
    digest = hashlib.sha256(body).hexdigest()[:32]
    print(f"  {path:<28} {r.status_code}  {len(body):>7} o  {digest}")

shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)
