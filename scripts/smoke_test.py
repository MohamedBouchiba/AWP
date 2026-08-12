"""Local smoke test — no Teamleader, no real DB.

Boots the Flask app against an isolated temp DATA_DIR with sync disabled, seeds
two fixture snapshots (one OLD-shape from before feedback round 2, one NEW-shape)
and hits every page — including the drawer and the analyse filters — asserting
200s with CSS present. Run after any change: `python scripts/smoke_test.py`.
"""
import os
import sys
import json
import shutil
import tempfile
import time

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
PLAIN = "plain@test.local"
if not store.get_user_by_email(PLAIN):
    store.create_user(PLAIN, "Plain", auth.hash_password("x"), is_admin=0)
uid_plain = store.get_user_by_email(PLAIN)["id"]
store.set_config("tl_users", [{"id": "u1", "name": "Wim Bonami"}])

# --- fixtures -------------------------------------------------------------
THIS_MONTH = time.strftime("%Y-%m", time.gmtime())

OLD_PHASE = [{"naam": "1. ADMINISTRATIE", "budget_eur": 250.0, "spent_eur": 428.0,
              "budget_hours": 3.0, "tracked_hours": 5.1, "pct": 171.2, "color": "darkred",
              "applicable": True, "started": True, "done": True, "glyph": "done"}]
store.upsert_snapshot({  # OLD shape: phases lack billed_eur/cost_eur; new cols None
    "project_id": "fx-old", "project_key": "A001", "titel": "A001 - Oud", "naam": "Oud",
    "adres": "", "status": "open", "is_architectuur": 1, "categorie": "Nieuwbouw",
    "contracttype": "", "verantw_arch": "XX", "verantw_medewerker": "",
    "budget_klant": 100000, "offerte_awp": 10000, "raming_vo": None,
    "uren_begroot": 10, "uren_gepresteerd": 5.1, "effectieve_kost": 331.5,
    "marge": None, "marge_pct": None, "summary_status": "over", "n_over": 1, "n_warn": 0,
    "cost_estimated": 1, "werfbezoeken": 2, "besprekingen": 1, "attention_note": "",
    "phases_json": json.dumps(OLD_PHASE), "synced_at": "2026-01-01T00:00:00Z"})

NEW_PHASE = [{"naam": "1. ADMINISTRATIE", "budget_eur": 1000.0, "spent_eur": 400.0,
              "budget_hours": 10.0, "tracked_hours": 3.0, "billed_eur": 500.0,
              "cost_eur": 200.0, "pct": 40.0, "color": "green",
              "applicable": True, "started": True, "done": False, "glyph": "progress"},
             {"naam": "2. SCHETSONTWERP", "budget_eur": 0.0, "spent_eur": 0.0,
              "budget_hours": 0.0, "tracked_hours": 0.0, "billed_eur": None,
              "cost_eur": None, "pct": None, "color": "none",
              "applicable": False, "started": False, "done": False, "glyph": "none"}]
store.upsert_snapshot({  # NEW shape (feedback round 2)
    "project_id": "fx-new", "project_key": "A002", "titel": "A002 - Nieuw", "naam": "Nieuw",
    "adres": "Teststraat 1", "status": "open", "is_architectuur": 1, "categorie": "Nieuwbouw",
    "contracttype": "Vast", "verantw_arch": "YY", "verantw_medewerker": "",
    "budget_klant": 200000, "offerte_awp": 20000, "raming_vo": None,
    "uren_begroot": 10, "uren_gepresteerd": 3.0, "effectieve_kost": 200.0,
    "gefactureerd": 500.0, "project_type": "architectuur",
    "activity_json": json.dumps([THIS_MONTH]),
    "marge": 300.0, "marge_pct": 60, "summary_status": "ok", "n_over": 0, "n_warn": 0,
    "cost_estimated": 0, "werfbezoeken": 1, "besprekingen": 0, "attention_note": "",
    # kost_bron 'rates' -> the per-person cost is reconcilable, so the column is
    # rendered (for admins). Under 'teamleader' it is deliberately hidden.
    "kost_bron": "rates",
    # cost 137 is deliberately DIFFERENT from effectieve_kost (200), so the
    # admin-gating assertion can't be satisfied by the project total.
    "uren_per_persoon_json": json.dumps([{"uid": "u1", "hours": 3.0, "cost": 137.0}]),
    "phases_json": json.dumps(NEW_PHASE), "synced_at": "2026-07-01T00:00:00Z"})

# A project whose phases have NO budgeted hours -> graph 2 must show its
# specific "fill in the time budgets in Teamleader" message.
ZERO_PHASE = [{"naam": "1. ADMINISTRATIE", "budget_eur": 100.0, "spent_eur": 50.0,
               "budget_hours": 0.0, "tracked_hours": 5.0, "billed_eur": None,
               "cost_eur": None, "pct": 50.0, "color": "green",
               "applicable": True, "started": True, "done": False, "glyph": "progress"}]
store.upsert_snapshot({
    "project_id": "fx-zero", "project_key": "A003", "titel": "A003 - Zero", "naam": "Zero",
    "adres": "", "status": "open", "is_architectuur": 1, "categorie": "", "contracttype": "",
    "verantw_arch": "", "verantw_medewerker": "", "budget_klant": None, "offerte_awp": None,
    "raming_vo": None, "uren_begroot": 0, "uren_gepresteerd": 5.0, "effectieve_kost": 325.0,
    "gefactureerd": None, "project_type": "", "activity_json": None,
    "marge": None, "marge_pct": None, "summary_status": "ok", "n_over": 0, "n_warn": 0,
    "cost_estimated": 1, "kost_bron": "flat", "werfbezoeken": 0, "besprekingen": 0,
    "attention_note": "", "phases_json": json.dumps(ZERO_PHASE),
    "synced_at": "2026-07-01T00:00:00Z"})

# Reproduces the A371 bug: a STALE row keeps the old margin (offerte - cost)
# while gefactureerd is NULL. Nothing may show a margin for it.
store.upsert_snapshot({
    "project_id": "fx-stale", "project_key": "A371", "titel": "A371 - Hoekje", "naam": "Hoekje",
    "adres": "", "status": "open", "is_architectuur": 1, "categorie": "Sloop & Herbouw",
    "contracttype": "", "verantw_arch": "SDS", "verantw_medewerker": "",
    "budget_klant": 350000, "offerte_awp": 17750, "raming_vo": 300000,
    "uren_begroot": 0, "uren_gepresteerd": 210.3, "effectieve_kost": 13669.0,
    "gefactureerd": None, "project_type": "", "activity_json": None,
    "marge": 4081.0, "marge_pct": 23, "summary_status": "over", "n_over": 1, "n_warn": 0,
    "cost_estimated": 1, "kost_bron": "flat", "werfbezoeken": 0, "besprekingen": 0,
    "attention_note": "", "phases_json": json.dumps(OLD_PHASE),
    "synced_at": "2026-01-01T00:00:00Z"})

# The upsert whitelist silently drops unknown keys -> assert the new columns
# actually round-trip, otherwise the tests below would pass for the wrong reason.
_rt = store.get_snapshot("fx-new")
assert _rt["kost_bron"] == "rates", "kost_bron not persisted (upsert cols whitelist!)"
assert json.loads(_rt["uren_per_persoon_json"])[0]["uid"] == "u1", "uren_per_persoon_json not persisted"
print("OK   new snapshot columns round-trip")

client = flask_app.test_client()
failures = []


def check(path, expect=200, needs_style=True, login=False, contains=None,
          excludes=None, as_user=None, raw=False):
    with client.session_transaction() as s:
        who = as_user if as_user is not None else (uid if login else None)
        if who is not None:
            s["uid"] = who
        else:
            s.pop("uid", None)
    r = client.get(path)
    body = r.get_data() if raw else r.get_data(as_text=True)
    ok = r.status_code == expect
    if ok and needs_style and expect == 200 and "<style>" not in body:
        ok = False
    if ok and contains is not None and contains not in body:
        ok = False
    if ok and excludes is not None and excludes in body:
        ok = False
    print(f"{'OK  ' if ok else 'FAIL'} {path:52s} -> {r.status_code}"
          f"{'' if ok else f' (expected {expect}, contains={contains!r}, excludes={excludes!r})'}")
    if not ok:
        failures.append(path)
    return r


# Public pages
check("/healthz", 200, needs_style=False)
check("/", 200)                       # onboarding wizard
check("/app/login", 200)              # dashboard login
check("/app", 302, needs_style=False, login=False)   # protected -> redirect
# Logged-in pages (fixtures present)
check("/app", 200, login=True, contains="A002")
check("/app/overzicht", 200, login=True)
check("/app/meldingen", 200, login=True)
check("/app/beheer", 200, login=True)
# Drawer: old-shape snapshot must render (defensive .get on new keys)
check("/app/project/fx-old", 200, needs_style=False, login=True, contains="A001")
check("/app/project/fx-new", 200, needs_style=False, login=True, contains="€500")
# Analyse. Assert on the SELECTION COUNT (not a project name: every project is
# listed in the filter <select>, which made a name-based assertion vacuous).
# fx-old/fx-stale/fx-zero have activity_json NULL -> never match a period;
# only fx-new has activity this month. 4 fixtures total.
check("/app/analyse", 200, login=True, contains="4 projecten in selectie")
check("/app/analyse?period=3", 200, login=True, contains="1 projecten in selectie")
check("/app/analyse?period=1", 200, login=True, contains="1 projecten in selectie")
# Custom range with only 'to' filled must NOT come back empty (240-month cap
# must drop the OLDEST months, not the recent ones).
check(f"/app/analyse?period=custom&to={THIS_MONTH}", 200, login=True,
      contains="1 projecten in selectie")
check(f"/app/analyse?period=custom&from={THIS_MONTH}&to={THIS_MONTH}", 200, login=True,
      contains="1 projecten in selectie")
# Explicit project selection wins over the period (documented precedence).
check("/app/analyse?pids=fx-old", 200, login=True, contains="1 projecten in selectie")
check("/app/analyse?pids=fx-old&pids=fx-new&period=1", 200, login=True,
      contains="2 projecten in selectie")

# --- feedback round 3 ------------------------------------------------------
# A371 regression: a stale row (marge set, gefactureerd NULL) must NEVER show a
# margin -- not in the drawer, not in the overview chip, not in the KPI.
r = check("/app/project/fx-stale", 200, needs_style=False, login=True, contains="A371")
assert "4.081" not in r.get_data(as_text=True), "STALE MARGIN LEAKED into the drawer"
r = check("/app", 200, login=True)
ov = r.get_data(as_text=True)
assert "€4.081" not in ov, "stale margin leaked into the overview chip"
# KPI 'Totale marge' must be 300 (fx-new only), not 4381 (fx-new + stale 4081)
assert "€300" in ov and "€4.381" not in ov, "stale margin polluted the Totale marge KPI"
print("OK   stale margin (A371) excluded from drawer, chip and KPI")

# Cost per person: hours for everyone, cost column ADMIN-ONLY.
# €137 is the per-person cost only (project total is €200), so this is unambiguous.
r = check("/app/project/fx-new", 200, needs_style=False, login=True, contains="Wim Bonami")
assert "€137" in r.get_data(as_text=True), "admin should see the per-person cost"
r = check("/app/project/fx-new", 200, needs_style=False, as_user=uid_plain,
          contains="Wim Bonami", excludes="€137")
print("OK   per-person cost is admin-only (hours visible to all)")

# Graph 6 + graph 4 regrouped on categorie; searchable multiselect + export button.
check("/app/analyse", 200, login=True, contains="Rendabiliteit per contracttype")
check("/app/analyse", 200, login=True, contains="Rendabiliteit per categorie")
check("/app/analyse", 200, login=True, contains='id="msPanel"')
check("/app/analyse", 200, login=True, contains='formaction="/app/analyse/export"')
# Graph 2 renders when budgeted hours exist, and shows its SPECIFIC empty
# message (not the generic one) for a project without any time budget.
check("/app/analyse", 200, login=True, contains="Gepresteerde vs begrote uren per fase")
check("/app/analyse?pids=fx-zero", 200, login=True, contains="Geen begrote uren in Teamleader")

# XLSX export: real xlsx (zip magic 'PK'), respects the filter, needs login.
check("/app/analyse/export", 302, needs_style=False, login=False)
r = check("/app/analyse/export", 200, needs_style=False, login=True, raw=True)
assert r.get_data()[:2] == b"PK", "export is not a real xlsx (missing zip magic)"
assert "spreadsheetml" in r.headers.get("Content-Type", ""), "wrong export mimetype"
assert "attachment" in r.headers.get("Content-Disposition", ""), "export not an attachment"
print("OK   xlsx export: zip magic, mimetype, attachment, login-protected")

# --- feedback round 4: phase taxonomy (lot 1) ------------------------------
from nacalc import phases as phases_mod   # noqa: E402


def post(path, data, expect=302):
    with client.session_transaction() as s:
        s["uid"] = uid
    r = client.post(path, data=data)
    ok = r.status_code == expect
    print(f"{'OK  ' if ok else 'FAIL'} POST {path:47s} -> {r.status_code}"
          f"{'' if ok else f' (expected {expect})'}")
    if not ok:
        failures.append(f"POST {path}")
    return r


# The Beheer card only lists phases the sync has actually seen. 'Nazorgdossier'
# is deliberately NOT in DEFAULT_ALIASES, so it exercises the suggestion path
# (the schetsontwerp pair is already shipped as a default and must stay silent).
store.set_config("seen_phase_names", ["1. ADMINISTRATIE", "2. Schetsontwerp",
                                      "2. Schetsontwerp/haalbaarheid", "3. VOORONTWERP",
                                      "6. Nazorg", "7. Nazorgdossier"])
check("/app/beheer", 200, login=True, contains="Fasen")
check("/app/beheer", 200, login=True, contains='name="form" value="phases"')
# Unknown merge -> offered as a suggestion; the already-aliased pair is not.
r = check("/app/beheer", 200, login=True, contains="Voorstellen op basis van Teamleader")
assert "nazorgdossier" in r.get_data(as_text=True), "la fusion inedite n'est pas proposee"

# Saving the form must persist exactly what was ticked/typed.
post("/app/beheer", {"form": "phases", "overhead": ["administratie"],
                     "aliases": ("schetsontwerp/haalbaarheid = schetsontwerp\n"
                                 "7. Nazorgdossier = 6. Nazorg\n\nbad line\n"),
                     "order": "1. ADMINISTRATIE\n3. VOORONTWERP\n"})
_tx = store.get_config("phase_taxonomy")
assert _tx["overhead"] == ["administratie"], f"overhead not saved: {_tx}"
assert _tx["aliases"] == {"schetsontwerp/haalbaarheid": "schetsontwerp",
                          "nazorgdossier": "nazorg"}, \
    f"aliases not saved/normalised: {_tx}"
assert _tx["order"] == ["administratie", "voorontwerp"], \
    f"order not normalised (numbers must be stripped): {_tx}"
print("OK   taxonomie sauvegardee et normalisee (numeros + casse)")

# With the alias saved, the suggestion must disappear (it is now applied).
check("/app/beheer", 200, login=True, excludes="Voorstellen op basis van Teamleader")

# The optimise button seeds aliases AND order from what Teamleader shows.
store.set_config("phase_taxonomy", phases_mod.DEFAULT_TAXONOMY | {"aliases": {}, "order": []})
post("/app/beheer", {"form": "phases_optimize"})
_tx = store.get_config("phase_taxonomy")
assert _tx["aliases"].get("schetsontwerp/haalbaarheid") == "schetsontwerp", \
    f"optimise did not propose the merge: {_tx}"
assert _tx["order"][:1] == ["administratie"], f"optimise did not order by number: {_tx}"
print("OK   'optimaliseer fasenamen' remplit alias + volgorde")

# A phase flagged overhead must NOT raise an alert either (same rule as the rollup).
store.set_config("phase_taxonomy", phases_mod.DEFAULT_TAXONOMY)
from nacalc import sync as sync_mod, calc as calc_mod, config as cfg_mod  # noqa: E402
_admin_red = calc_mod.build_phases(
    [{"name": "1. ADMINISTRATIE", "budget_eur": 250.0, "spent_eur": 900.0,
      "tracked_hours": 9.0, "budget_hours": 3.0}],
    cfg_mod.DEFAULT_THRESHOLDS, phases_mod.DEFAULT_TAXONOMY)
sync_mod._make_meldingen({"project_id": "fx-oh", "project_key": "A999", "naam": "Overhead",
                          "phases_json": json.dumps(_admin_red)})
assert not [m for m in store.list_meldingen() if m["project_id"] == "fx-oh"], \
    "une fase overhead a genere une melding"
print("OK   une fase overhead ne genere aucune melding")

# --- feedback round 4: status basis + manual invoicing (lot 2) -------------
# Hours bar must use the STARTED-phase columns when they are present.
store.upsert_snapshot(dict(store.get_snapshot("fx-new"),
                           uren_begroot_gestart=5.0, uren_gepresteerd_gestart=3.0))
check("/app", 200, login=True, contains="3.0 / 5.0u")
print("OK   la barre d'uren utilise le budget des fases gestartes")

# Manual invoicing: admin-only, survives a sync, and flows into the margin.
r = client.post("/app/project/fx-new/gefactureerd", data={"bedrag": "250"})
assert r.status_code in (302, 303), f"manual invoice POST -> {r.status_code}"
assert store.get_snapshot("fx-new")["gefactureerd_manueel"] == 250.0, "montant non persiste"
# The sync's upsert must NOT wipe it (the column is outside the write whitelist).
store.upsert_snapshot(dict(store.get_snapshot("fx-new"), gefactureerd=500.0))
assert store.get_snapshot("fx-new")["gefactureerd_manueel"] == 250.0, \
    "la sync a ecrase la facturation manuelle"
print("OK   facturation manuelle persistee et non ecrasee par la sync")

# Margin is derived live: 500 (TL) + 250 (manueel) - 200 (kost) = 550.
r = check("/app", 200, login=True, contains="€550")
assert "€300" not in r.get_data(as_text=True), "l'ancienne marge stockee est encore affichee"
print("OK   marge recalculee en direct sur le total facture")

with client.session_transaction() as s:
    s["uid"] = uid_plain
r = client.post("/app/project/fx-new/gefactureerd", data={"bedrag": "999"})
assert r.status_code == 403, f"non-admin devrait recevoir 403, recu {r.status_code}"
assert store.get_snapshot("fx-new")["gefactureerd_manueel"] == 250.0, "non-admin a pu ecrire"
print("OK   saisie manuelle reservee aux admins")

# The basis toggle is reversible from Beheer, no redeploy needed.
check("/app/beheer", 200, login=True, contains='name="status_basis"')
post("/app/beheer", {"form": "basis", "status_basis": "spent"})
assert store.get_config("status_basis") == "spent", "bascule non sauvegardee"
post("/app/beheer", {"form": "basis", "status_basis": "cost"})
assert store.get_config("status_basis") == "cost", "retour a la base cout impossible"
post("/app/beheer", {"form": "basis", "status_basis": "onzin"})
assert store.get_config("status_basis") == "cost", "valeur invalide acceptee"
print("OK   bascule de base reversible et validee")

shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)

if failures:
    print("\nSMOKE TEST FAILED:", failures)
    sys.exit(1)
print("\nAll smoke checks passed.")
