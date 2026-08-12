"""Local smoke test — no Teamleader, no real DB.

Boots the Flask app against an isolated temp DATA_DIR with sync disabled, seeds
two fixture snapshots (one OLD-shape from before feedback round 2, one NEW-shape)
and hits every page — including the drawer and the analyse filters — asserting
200s with CSS present. Run after any change: `python scripts/smoke_test.py`.
"""
import os
import re
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

# Saving the form must persist exactly what was ticked/typed. The checkbox reads
# "counts towards the status", so overhead is everything SHOWN but not ticked.
post("/app/beheer", {"form": "phases",
                     "shown": "administratie,schetsontwerp,voorontwerp",
                     "meetellen": ["schetsontwerp", "voorontwerp"],
                     "aliases": ("schetsontwerp/haalbaarheid = schetsontwerp\n"
                                 "7. Nazorgdossier = 6. Nazorg\n\nbad line\n"),
                     "order": "1. ADMINISTRATIE\n3. VOORONTWERP\n"})
_tx = store.get_config("phase_taxonomy")
assert _tx["overhead"] == ["administratie"], f"overhead not saved: {_tx}"
# A phase the form never listed must keep its setting, not be silently reset.
store.set_config("phase_taxonomy", dict(_tx, overhead=["administratie", "nazorg"]))
post("/app/beheer", {"form": "phases", "shown": "administratie",
                     "meetellen": [], "aliases": "", "order": ""})
assert set(store.get_config("phase_taxonomy")["overhead"]) == {"administratie", "nazorg"}, \
    "une fase absente du formulaire a perdu son reglage"
store.set_config("phase_taxonomy", _tx)
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

# --- feedback round 4: overzicht selection (lot 3) -------------------------
# "Selectie van laatste maand, 3 maanden, jaar en alles" + "op verantwoordelijke".
check("/app", 200, login=True, contains='name="period"')
check("/app", 200, login=True, contains='name="verantw"')
# Only fx-new has activity this month -> a period must shrink the table AND the KPIs.
r = check("/app?period=1", 200, login=True, contains="1 van 4 projecten")
body = r.get_data(as_text=True)
assert "A002" in body and "A001" not in body, "le filtre periode ne filtre pas les lignes"
# KPI 'Lopende projecten' must be 1, not 4 -> the cards follow the selection.
assert '<div class="val">1</div>' in body, "les KPI ne suivent pas le filtre periode"
print("OK   filtre periode : lignes ET cartes KPI suivent")

r = check("/app?verantw=YY", 200, login=True, contains="A002")
assert "A001" not in r.get_data(as_text=True), "le filtre verantwoordelijke ne filtre pas"
check("/app?verantw=ZZ-onbekend", 200, login=True, contains="0 van 4 projecten")
print("OK   filtre verantwoordelijke")

# Combined, and the reset link must be offered whenever a selection is active.
r = check("/app?period=1&verantw=YY", 200, login=True, contains="1 van 4 projecten")
assert 'href="/app"' in r.get_data(as_text=True), "pas de lien de reinitialisation"
# No selection -> no count pill (nothing is being hidden).
r = check("/app", 200, login=True)
assert "van 4 projecten" not in r.get_data(as_text=True), \
    "le compteur s'affiche alors qu'aucun filtre n'est actif"
print("OK   filtres combines + reinitialisation")

# --- feedback round 4: visits moved up (lot 4) -----------------------------
# "Werfbezoeken en besprekingen mag hoger zichtbaar zijn, nu is er wat
# scrolwerk." They must now sit in the header grid, ABOVE the phase list.
r = check("/app/project/fx-new", 200, needs_style=False, login=True, contains="Werfbezoeken")
body = r.get_data(as_text=True)
assert body.index("Werfbezoeken") < body.index("Voortgang per fase"), \
    "les werfbezoeken sont toujours sous la liste des fases"
assert body.count("Werfbezoeken") == 1, "bloc werfbezoeken duplique"
print("OK   werfbezoeken remontes au-dessus des fases")

# --- feedback round 4: finished projects (lot 5) ---------------------------
# Teamleader keeps all 187 AWP projects "open", so "afgerond" is derived from
# inactivity. fx-new has activity THIS month; fx-old has activity 8 months ago.
OLD_MONTH = time.strftime("%Y-%m", time.gmtime(time.time() - 250 * 86400))
store.upsert_snapshot(dict(store.get_snapshot("fx-old"),
                           activity_json=json.dumps([OLD_MONTH])))
check("/app/analyse", 200, login=True, contains='name="dossier"')
r = check("/app/analyse?dossier=afgerond", 200, login=True, contains="1 projecten in selectie")
r = check("/app/analyse?dossier=lopend", 200, login=True, contains="3 projecten in selectie")
print("OK   filtre lopend / afgerond sur l'analyse")

# The manual override wins over the automatic rule, in both directions.
r = client.post("/app/project/fx-old/afgerond", data={"afgerond": "0"})
assert r.status_code in (302, 303)
check("/app/analyse?dossier=afgerond", 200, login=True, contains="0 projecten in selectie")
r = client.post("/app/project/fx-new/afgerond", data={"afgerond": "1"})
assert r.status_code in (302, 303)
check("/app/analyse?dossier=afgerond", 200, login=True, contains="1 projecten in selectie")
# Back to automatic.
client.post("/app/project/fx-old/afgerond", data={"afgerond": ""})
client.post("/app/project/fx-new/afgerond", data={"afgerond": ""})
check("/app/analyse?dossier=afgerond", 200, login=True, contains="1 projecten in selectie")
print("OK   surcharge manuelle prioritaire, et retour a l'automatique")

# The override must survive a sync, like the manual invoice does.
client.post("/app/project/fx-old/afgerond", data={"afgerond": "0"})
store.upsert_snapshot(dict(store.get_snapshot("fx-old"), naam="Oud (resync)"))
assert store.get_snapshot("fx-old")["afgerond_manueel"] == 0, "la sync a ecrase la surcharge"
client.post("/app/project/fx-old/afgerond", data={"afgerond": ""})
print("OK   surcharge afgerond non ecrasee par la sync")

# The export honours the same filter as the page.
r = check("/app/analyse/export?dossier=afgerond", 200, needs_style=False, login=True, raw=True)
assert r.get_data()[:2] == b"PK", "export cassé par le filtre dossier"
# Non-admin cannot flip the flag.
with client.session_transaction() as s:
    s["uid"] = uid_plain
assert client.post("/app/project/fx-old/afgerond", data={"afgerond": "1"}).status_code == 403
print("OK   export filtre + surcharge reservee aux admins")

# --- feedback round 4: Analyse 2 + chronological order (lot 6) -------------
# Give fx-new phases with a cost, in DELIBERATELY reversed quote order, so the
# chronological sort has something real to prove.
CHRONO = calc_mod.build_phases([
    {"name": "9. NAZORG", "budget_eur": 1000.0, "spent_eur": 500.0, "cost_eur": 900.0,
     "tracked_hours": 9.0, "budget_hours": 10.0},
    {"name": "3. VOORONTWERP", "budget_eur": 2000.0, "spent_eur": 500.0, "cost_eur": 400.0,
     "tracked_hours": 4.0, "budget_hours": 20.0},
    {"name": "1. ADMINISTRATIE", "budget_eur": 100.0, "spent_eur": 50.0, "cost_eur": 50.0,
     "tracked_hours": 1.0, "budget_hours": 2.0},
], cfg_mod.DEFAULT_THRESHOLDS, phases_mod.DEFAULT_TAXONOMY)
store.upsert_snapshot(dict(store.get_snapshot("fx-new"), phases_json=json.dumps(CHRONO)))

check("/app/analyse2", 200, login=True, contains="Kostprijs vs geofferteerd budget per fase")
check("/app/analyse2", 200, login=True, contains="Rendabiliteit per categorie (offerte")
# Analyse 2 must not mention invoicing anywhere -- that is its whole purpose.
r = check("/app/analyse2", 200, login=True)
an2 = r.get_data(as_text=True)
body_from_filters = an2[an2.index('class="grid2"'):]
assert "Gefactureerd" not in body_from_filters, "Analyse 2 parle encore de facturation"
print("OK   Analyse 2 : graphes offerte/kostprijs, zero facturation")

# NAZORG (9) must render AFTER ADMINISTRATIE (1) and VOORONTWERP (3), even though
# NAZORG has by far the worst percentage -> proves the sort is chronological.
for page in ("/app/analyse", "/app/analyse2"):
    r = check(page, 200, login=True, contains="NAZORG")
    b = r.get_data(as_text=True)
    g = b[b.index('class="grid2"'):]
    assert g.index("ADMINISTRATIE") < g.index("VOORONTWERP") < g.index("NAZORG"), \
        f"{page}: les fases ne sont pas en ordre chronologique"
print("OK   fases en ordre chronologique sur les deux analyses")

# Analyse 2 shares the filter machinery, and its export is a real xlsx.
check("/app/analyse2?period=1", 200, login=True, contains="1 projecten in selectie")
check("/app/analyse2?dossier=afgerond", 200, login=True, contains="1 projecten in selectie")
r = check("/app/analyse2/export", 200, needs_style=False, login=True, raw=True)
assert r.get_data()[:2] == b"PK", "export Analyse 2 n'est pas un xlsx"
assert "analyse2" in r.headers.get("Content-Disposition", ""), "nom de fichier export incorrect"
check("/app/analyse2/export", 302, needs_style=False, login=False)
print("OK   Analyse 2 : filtres partages + export xlsx protege")

# Both analyses reachable from the sidebar.
check("/app", 200, login=True, contains='href="/app/analyse2"')

# --- feedback round 4: alert emails (lot 7) --------------------------------
# "wel geen spam per tijdregistratie, dus er moet een manier zijn om deze
# mailing te dempen als er een analyse van het budget/timing is gebeurd"
from nacalc import mailer as mailer_mod   # noqa: E402

OVER = calc_mod.build_phases([
    {"name": "3. VOORONTWERP", "budget_eur": 1000.0, "spent_eur": 1500.0, "cost_eur": 1500.0,
     "tracked_hours": 20.0, "budget_hours": 10.0},
    {"name": "4. BOUWAANVRAAG", "budget_eur": 1000.0, "spent_eur": 900.0, "cost_eur": 900.0,
     "tracked_hours": 12.0, "budget_hours": 10.0},
], cfg_mod.DEFAULT_THRESHOLDS, phases_mod.DEFAULT_TAXONOMY)
SNAP_OVER = {"project_id": "fx-mail", "project_key": "A500", "naam": "Mail",
             "verantw_arch": "WB", "phases_json": json.dumps(OVER)}

# 1. The persistence fix: a repeated sync must NOT resurrect a read alert.
sync_mod._make_meldingen(SNAP_OVER)
assert store.count_unseen_meldingen() == 2, "2 meldingen attendues (over + dreigt over)"
store.mark_meldingen_seen()
sync_mod._make_meldingen(SNAP_OVER)          # the hourly sync runs again
assert store.count_unseen_meldingen() == 0, \
    "la sync a recree les meldingen -> le badge repasse en rouge toutes les heures"
print("OK   une re-sync ne ressuscite pas une melding deja lue")

# 2. A phase dropping back below threshold removes only its own alert.
BETTER = calc_mod.build_phases([
    {"name": "3. VOORONTWERP", "budget_eur": 1000.0, "spent_eur": 1500.0, "cost_eur": 1500.0,
     "tracked_hours": 20.0, "budget_hours": 10.0},
    {"name": "4. BOUWAANVRAAG", "budget_eur": 1000.0, "spent_eur": 100.0, "cost_eur": 100.0,
     "tracked_hours": 2.0, "budget_hours": 10.0},
], cfg_mod.DEFAULT_THRESHOLDS, phases_mod.DEFAULT_TAXONOMY)
sync_mod._make_meldingen(dict(SNAP_OVER, phases_json=json.dumps(BETTER)))
kept = [m for m in store.list_meldingen() if m["project_id"] == "fx-mail"]
assert len(kept) == 1 and kept[0]["phase_naam"] == "3. VOORONTWERP", \
    f"purge incorrecte des meldingen retombees: {[m['phase_naam'] for m in kept]}"
print("OK   une fase repassee sous le seuil perd sa melding, les autres restent")

# 3. THE anti-spam guarantee: three syncs in a row -> exactly one email.
sync_mod._make_meldingen(SNAP_OVER)
os.environ.update(SMTP_HOST="smtp.test", SMTP_FROM="dash@awpburo.be", MAIL_DRY_RUN="1")
store.set_config("verantw_emails", {"WB": "wb@awpburo.be"})
assert mailer_mod.is_configured() and mailer_mod.is_dry_run()
n1 = sync_mod.send_digests()
n2 = sync_mod.send_digests()
n3 = sync_mod.send_digests()
assert (n1, n2, n3) == (1, 0, 0), f"attendu 1 seul envoi, obtenu {(n1, n2, n3)}"
print("OK   3 syncs consecutives = 1 seul mail (groupe par verantwoordelijke)")

# 4. Snooze stops the mail without hiding the alert.
store.mark_notified([m["id"] for m in store.list_meldingen()], "2000-01-01T00:00:00Z")
r = client.post("/app/meldingen/snooze", data={"project_id": "fx-mail", "days": "14"})
assert r.status_code in (302, 303)
assert "fx-mail" in store.snoozed_projects(), "snooze non enregistre"
assert sync_mod.send_digests() == 0, "un projet dempte a quand meme envoye un mail"
assert any(m["project_id"] == "fx-mail" for m in store.list_meldingen()), \
    "le snooze a fait disparaitre la melding de la page"
check("/app/meldingen", 200, login=True, contains="Gedempt")
print("OK   snooze : plus de mail, melding toujours visible")

# 5. No address for that owner -> no mail, and notified_at stays untouched so
#    nothing is silently swallowed once the address is filled in.
store.set_config("verantw_emails", {})
store.mark_notified([m["id"] for m in store.list_meldingen()], "2000-01-01T00:00:00Z")
store.snooze_project("fx-mail", "2000-01-01T00:00:00Z")     # expire the snooze
assert sync_mod.send_digests() == 0, "mail envoye sans adresse connue"
store.set_config("verantw_emails", {"WB": "wb@awpburo.be"})
assert sync_mod.send_digests() == 1, "le mail ne part pas une fois l'adresse remplie"
print("OK   sans adresse : rien n'est envoye ni perdu")

# 6. Not configured -> feature inert, and Beheer says so.
for k in ("SMTP_HOST", "SMTP_FROM"):
    os.environ.pop(k, None)
assert not mailer_mod.is_configured()
assert sync_mod.send_digests() == 0, "envoi tente sans configuration SMTP"
check("/app/beheer", 200, login=True, contains="Niet geconfigureerd")
check("/app/beheer", 200, login=True, contains='name="form" value="mail"')
print("OK   sans SMTP : fonctionnalite inerte et signalee en Beheer")

# --- l'exclusion doit agir IMMEDIATEMENT, sans attendre une sync -----------
# C'est le defaut signale : l'indicateur overhead etait fige dans le cache, donc
# cocher la case ne changeait rien avant la sync suivante (jusqu'a 20 min).
OH_ONLY = calc_mod.build_phases([
    {"name": "1. ADMINISTRATIE", "budget_eur": 249.90, "spent_eur": 945.0, "cost_eur": 945.0,
     "tracked_hours": 11.0, "budget_hours": 3.0},
    {"name": "3. VOORONTWERP", "budget_eur": 10000.0, "spent_eur": 900.0, "cost_eur": 900.0,
     "tracked_hours": 12.0, "budget_hours": 100.0},
], cfg_mod.DEFAULT_THRESHOLDS, {"aliases": {}, "order": [], "overhead": [], "labels": {}})
store.upsert_snapshot({
    "project_id": "fx-oh", "project_key": "A900", "titel": "A900 - Overhead", "naam": "Overhead",
    "adres": "", "status": "open", "is_architectuur": 1, "categorie": "", "contracttype": "",
    "verantw_arch": "WB", "verantw_medewerker": "", "budget_klant": None, "offerte_awp": None,
    "raming_vo": None, "uren_begroot": 103.0, "uren_gepresteerd": 23.0,
    "uren_begroot_gestart": 103.0, "uren_gepresteerd_gestart": 23.0,
    "effectieve_kost": 1845.0, "gefactureerd": None, "project_type": "", "activity_json": None,
    "marge": None, "marge_pct": None, "summary_status": "over", "n_over": 1, "n_warn": 0,
    "cost_estimated": 0, "kost_bron": "teamleader", "werfbezoeken": 0, "besprekingen": 0,
    "attention_note": "", "phases_json": json.dumps(OH_ONLY),
    "synced_at": "2026-08-12T00:00:00Z"})
# Le snapshot est ecrit avec overhead=[] -> administratie compte -> 'over'.
assert store.get_snapshot("fx-oh")["summary_status"] == "over"

def _status_of(pid, key):
    r = client.get("/app")
    m = re.search(r'<tr class="row-(\w*)"[^>]*data-nr="' + key + r'"', r.get_data(as_text=True))
    return (m.group(1) or "none") if m else "ABSENT"

with client.session_transaction() as s:
    s["uid"] = uid
# 1) administratie comptee -> le dossier est 'over'
post("/app/beheer", {"form": "phases", "shown": "administratie,voorontwerp",
                     "meetellen": ["administratie", "voorontwerp"], "aliases": "", "order": ""})
assert _status_of("fx-oh", "A900") == "over", "administratie cochee devrait peser sur le statut"
r = client.get("/app/project/fx-oh")
assert "Over budget" in r.get_data(as_text=True), "le drawer ne suit pas le reglage"

# 2) on la decoche -> effet IMMEDIAT, sans aucune sync
post("/app/beheer", {"form": "phases", "shown": "administratie,voorontwerp",
                     "meetellen": ["voorontwerp"], "aliases": "", "order": ""})
assert _status_of("fx-oh", "A900") == "ok", \
    "decocher administratie n'a eu aucun effet immediat sur l'apercu"
r = client.get("/app/project/fx-oh")
body = r.get_data(as_text=True)
assert "Over budget" not in body, "le drawer affiche encore 'Over budget'"
# ... et l'infobulle des uren doit nommer la fase overhead
assert "budgetstatus" in body, "l'infobulle n'explique pas le sort de la fase overhead"
# Le cache lui-meme n'a PAS ete reecrit : c'est bien un recalcul a la lecture.
assert store.get_snapshot("fx-oh")["summary_status"] == "over"
print("OK   cocher/decocher une fase change le dossier immediatement")

# 3) on la recoche -> retour a 'over'
post("/app/beheer", {"form": "phases", "shown": "administratie,voorontwerp",
                     "meetellen": ["administratie", "voorontwerp"], "aliases": "", "order": ""})
assert _status_of("fx-oh", "A900") == "over", "le reglage n'est pas reversible"
print("OK   reversible dans les deux sens")

# L'interface de reglage doit etre le tableau, avec l'impact chiffre.
r = check("/app/beheer", 200, login=True, contains='name="meetellen"')
be = r.get_data(as_text=True)
assert 'class="ph-grid"' in be, "la carte Fasen n'utilise pas la grille compacte"
assert 'type="checkbox" name="meetellen"' in be, "ce ne sont pas de vraies cases a cocher"
assert 'name="shown"' in be, "le formulaire ne dit pas quelles fases il a listees"
assert "boven drempel" in be, "l'indication d'impact est absente"
print("OK   reglage des fases : cases a cocher en grille compacte + impact")

# La bulle d'info a remplace le long texte bleu dans la fiche.
r = client.get("/app/project/fx-new")
body = r.get_data(as_text=True)
assert 'class="ib-pop"' in body, "pas d'encart d'info dans la fiche"
assert body.count("Automatisch: afgerond zodra") == 1, "regle afgerond en double"
# L'encart des uren doit rester COURT : deux lignes, pas la liste des inclus.
inner = re.search(r'Welke fasen zitten in dit cijfer\?</b>(.*?)</span></span>', body, re.S)
assert inner, "encart uren introuvable"
assert inner.group(1).count('class="ib-r') <= 2, \
    f"l'encart liste trop de lignes : {inner.group(1)[:300]}"
assert "meegeteld" in inner.group(1), "l'encart ne dit pas combien de fases sont comptees"
# La liste entre parentheses doit rester plafonnee, meme sur un dossier ou
# aucune fase n'a demarre (10 fases exclues -> 3 noms + "+7 andere").
MANY = calc_mod.build_phases(
    [{"name": f"{i}. FASE{i}", "budget_eur": 100.0, "spent_eur": 0.0,
      "cost_eur": None, "tracked_hours": 0.0, "budget_hours": 5.0} for i in range(1, 11)],
    cfg_mod.DEFAULT_THRESHOLDS, phases_mod.DEFAULT_TAXONOMY)
store.upsert_snapshot(dict(store.get_snapshot("fx-zero"), project_id="fx-many",
                           project_key="A901", phases_json=json.dumps(MANY)))
mb = client.get("/app/project/fx-many").get_data(as_text=True)
mi = re.search(r'ib-no">([^<]*)</span>', mb)
assert mi and "andere" in mi.group(1) and mi.group(1).count(",") <= 3, \
    f"la liste des fases exclues n'est pas plafonnee : {mi.group(1) if mi else None}"
print("OK   encarts d'info structures, courts et plafonnes")

# Le slash orphelin : il faut une fase SANS budget d'heures pour l'exercer.
# fx-zero a exactement ca (budget_hours=0) -- la fixture precedente avait un
# budget partout, ce qui laissait passer la ligne par fase et la barre du tableau.
for page in ("/app", "/app/project/fx-zero", "/app/project/fx-old"):
    b = client.get(page).get_data(as_text=True)
    assert " / —" not in b and "/—" not in b, f"slash sans valeur encore present sur {page}"
b = client.get("/app/project/fx-zero").get_data(as_text=True)
assert "5.0u" in b, "les heures prestees ont disparu avec le slash"
# L'infobulle des pastilles ne doit plus coller un % en euros a des heures.
assert "% van het budget" in client.get("/app").get_data(as_text=True), \
    "l'infobulle des pastilles ne precise pas que le % porte sur le budget"
print("OK   plus de slash orphelin (apercu, fiches) et infobulle des pastilles corrigee")

# --- robustesse de la synchronisation --------------------------------------
# Vu en production : le conteneur redemarre pendant une sync, `running` reste a 1
# et run_full() sort immediatement pour toujours -> le cache gele en silence.
store.set_sync_state(running=1, last_run_at=store.now_iso())
store.init_db()                       # = ce que fait un demarrage de processus
assert store.get_sync_state()["running"] == 0, \
    "un demarrage ne remet pas le drapeau 'running' a zero"
print("OK   un redemarrage debloque une sync interrompue")

# Et si le drapeau se coince malgre tout, un run trop vieux est considere mort.
store.set_sync_state(running=1, last_run_at="2020-01-01T00:00:00Z")
assert sync_mod._age_minutes("2020-01-01T00:00:00Z") > sync_mod.STALE_RUN_MINUTES
store.set_sync_state(running=1, last_run_at=store.now_iso())
assert sync_mod._age_minutes(store.now_iso()) < 1, "l'age d'une sync fraiche est faux"
assert sync_mod._age_minutes("pas une date") is None, "date invalide non geree"
store.set_sync_state(running=0)
print("OK   garde-fou d'anciennete sur les syncs bloquees")

# La pastille doit dire quand les donnees sont en retard, pas juste une heure.
store.set_sync_state(last_ok_at="2020-01-01T00:00:00Z", last_error=None)
r = check("/app", 200, login=True, contains="achterstallig")
assert 'class="pill stale"' in r.get_data(as_text=True), "la pastille ne signale pas le retard"
store.set_sync_state(last_ok_at=store.now_iso())
r = check("/app", 200, login=True)
assert "achterstallig" not in r.get_data(as_text=True), "retard signale a tort"
print("OK   la pastille signale une sync en retard")

shutil.rmtree(os.environ["DATA_DIR"], ignore_errors=True)

if failures:
    print("\nSMOKE TEST FAILED:", failures)
    sys.exit(1)
print("\nAll smoke checks passed.")
