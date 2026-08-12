"""Unit tests for the pure calculation layer — no Flask, no DB, no Teamleader.

`nacalc/calc.py` was written to be IO-free and unit-testable, but had no tests.
These lock in the CURRENT behaviour before any change, so a regression shows up
as a failing assertion instead of a wrong number on the client's dashboard.

The centrepiece is the **A346 golden master**: the nine real phases of
"A346 - Elsakkerweg Sint-Martens-Latem", read straight off the production
Teamleader account (projects.info + projectGroups.list, read-only). It is the
project the client asked about, so every change to the status pipeline must be
re-checked against it.

Run: `python scripts/unit_test.py`
"""
import os
import sys

# Make the repo root importable when run as `python scripts/unit_test.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nacalc import calc, config, phases, sync, teamleader as TL  # noqa: E402

failures = []


def eq(label, got, want):
    ok = got == want
    print(f"{'OK  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       got  {got!r}\n       want {want!r}")
        failures.append(label)


def close(label, got, want, tol=0.05):
    ok = got is not None and abs(got - want) <= tol
    print(f"{'OK  ' if ok else 'FAIL'} {label}")
    if not ok:
        print(f"       got  {got!r}\n       want {want!r} (±{tol})")
        failures.append(label)


TH = config.DEFAULT_THRESHOLDS          # {"amber": 80, "red": 100, "darkred": 115}


# --------------------------------------------------------------------------
# 1. color_for — the ONLY place the thresholds are applied
# --------------------------------------------------------------------------
print("\n--- color_for (seuils 80/100/115) ---")
eq("pct None -> 'none' (fase sans budget)", calc.color_for(None, TH), "none")
eq("pct 0 -> green", calc.color_for(0, TH), "green")
eq("pct 79.9 -> green", calc.color_for(79.9, TH), "green")
eq("pct 80 -> amber (>= amber)", calc.color_for(80, TH), "amber")
eq("pct 99.9 -> amber", calc.color_for(99.9, TH), "amber")
# Deliberately asymmetric in calc.py: red is `> red`, not `>= red`.
eq("pct 100 -> amber (red est un > strict)", calc.color_for(100, TH), "amber")
eq("pct 100.1 -> red", calc.color_for(100.1, TH), "red")
eq("pct 114.9 -> red", calc.color_for(114.9, TH), "red")
eq("pct 115 -> darkred (>= darkred)", calc.color_for(115, TH), "darkred")
eq("pct 250.6 -> darkred", calc.color_for(250.6, TH), "darkred")


# --------------------------------------------------------------------------
# 2. _phase_sort_key — numbered phases first, in order; the rest alphabetical
# --------------------------------------------------------------------------
print("\n--- ordre des fases ---")
names = ["9. BOUWCOORDINATIE", "MEERWERKEN", "1. ADMINISTRATIE", "10. EXTRA", "2. SCHETS"]
eq("tri par numero de tete, non numerotes en dernier",
   sorted(names, key=calc._phase_sort_key),
   ["1. ADMINISTRATIE", "2. SCHETS", "9. BOUWCOORDINATIE", "10. EXTRA", "MEERWERKEN"])
eq("nom None ne casse pas le tri", calc._phase_sort_key(None), (1, ""))


# --------------------------------------------------------------------------
# 3. parse_money — free-text custom fields (Budget BH / Raming AWP)
# --------------------------------------------------------------------------
print("\n--- parse_money ---")
eq("'€ 350.000,00' -> 350000.0", sync.parse_money("€ 350.000,00"), 350000.0)
eq("'350000' -> 350000.0", sync.parse_money("350000"), 350000.0)
eq("'1.234' (milliers) -> 1234.0", sync.parse_money("1.234"), 1234.0)
eq("'1,5' (virgule decimale) -> 1.5", sync.parse_money("1,5"), 1.5)
eq("None -> None", sync.parse_money(None), None)
eq("'' -> None", sync.parse_money(""), None)
eq("texte libre -> None", sync.parse_money("nvt"), None)


# --------------------------------------------------------------------------
# 4. Teamleader money/time helpers — the real-zero vs missing distinction
# --------------------------------------------------------------------------
print("\n--- helpers Teamleader ---")
eq("amount({amount: 12.5}) -> 12.5", TL.amount({"amount": 12.5}), 12.5)
# amount() collapses "absent" into 0.0 -- a known trap, locked in here on purpose.
eq("amount(None) -> 0.0 (ecrase l'absence)", TL.amount(None), 0.0)
eq("amount_or_none(None) -> None", TL.amount_or_none(None), None)
eq("amount_or_none({amount: None}) -> None", TL.amount_or_none({"amount": None}), None)
eq("amount_or_none({amount: 0}) -> 0.0 (vrai zero)", TL.amount_or_none({"amount": 0}), 0.0)
eq("hours({value: 3600}) -> 1.0", TL.hours({"value": 3600}), 1.0)
eq("hours(None) -> 0.0", TL.hours(None), 0.0)


# --------------------------------------------------------------------------
# 5. GOLDEN MASTER — A346, les 9 vraies fases de production
#    Relevé read-only le 2026-08-12 sur le compte Teamleader d'AWP Buro.
#    Projet: price=63860.78  cost=37928.54  amount_billed=11226.54
#            time_tracked=684.82u  time_estimated=736.06u
# --------------------------------------------------------------------------
A346 = [
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
    # NAZORG: budgeted but untouched -> its 73.5 budgeted hours must NOT dilute
    # the hours bar (this is the client's "A346 paradox").
    {"name": "7. NAZORG", "budget_eur": 6247.50, "spent_eur": 0.0,
     "cost_eur": None, "billed_eur": None, "tracked_hours": 0.0, "budget_hours": 73.50},
    # MEERWERKEN: worked but never quoted (budget 0) -> shown, never a "overrun".
    {"name": "8. MEERWERKEN", "budget_eur": 0.0, "spent_eur": 1380.68,
     "cost_eur": 1211.58, "billed_eur": None, "tracked_hours": 16.24, "budget_hours": 1.00},
    {"name": "9. BOUWCOORDINATIE", "budget_eur": 6247.50, "spent_eur": 345.00,
     "cost_eur": 287.50, "billed_eur": None, "tracked_hours": 3.83, "budget_hours": 73.50},
]

print("\n--- A346 : build_phases (base actuelle = spent/budget) ---")
ph = calc.build_phases(A346, TH)
by = {p["naam"]: p for p in ph}

eq("9 fases, ordre chronologique conserve",
   [p["naam"] for p in ph],
   ["1. ADMINISTRATIE", "2. SCHETSONTWERP", "3. VOORONTWERP", "4. BOUWAANVRAAG",
    "5. UITVOERINGSDOSSIER", "6. COMPLETE WERFOPVOLGING", "7. NAZORG",
    "8. MEERWERKEN", "9. BOUWCOORDINATIE"])

# Percentages, straight from the live account.
for naam, want_pct in [("1. ADMINISTRATIE", 48.0), ("2. SCHETSONTWERP", 46.9),
                       ("3. VOORONTWERP", 133.9), ("4. BOUWAANVRAAG", 68.8),
                       ("5. UITVOERINGSDOSSIER", 250.6), ("6. COMPLETE WERFOPVOLGING", 70.6),
                       ("7. NAZORG", 0.0), ("9. BOUWCOORDINATIE", 5.5)]:
    eq(f"pct {naam} = {want_pct}", by[naam]["pct"], want_pct)
eq("pct 8. MEERWERKEN = None (budget 0)", by["8. MEERWERKEN"]["pct"], None)

eq("3. VOORONTWERP -> darkred", by["3. VOORONTWERP"]["color"], "darkred")
eq("5. UITVOERINGSDOSSIER -> darkred", by["5. UITVOERINGSDOSSIER"]["color"], "darkred")
eq("1. ADMINISTRATIE -> green", by["1. ADMINISTRATIE"]["color"], "green")

eq("7. NAZORG : pas gestart (0 EUR, 0 h)", by["7. NAZORG"]["started"], False)
eq("8. MEERWERKEN : gestart mais hors budget",
   (by["8. MEERWERKEN"]["started"], by["8. MEERWERKEN"]["applicable"]), (True, False))

print("\n--- A346 : project_summary ---")
summ = calc.project_summary(ph)
# THE answer to the client: two phases are genuinely over budget.
eq("statut projet = 'over'", summ["status"], "over")
eq("2 fases en depassement (VOORONTWERP + UITVOERINGSDOSSIER)", summ["n_over"], 2)
eq("0 fase en 'dreigt over'", summ["n_warn"], 0)
# 9 fases - NAZORG (non gestart) - MEERWERKEN (sans budget) - ADMINISTRATIE
# (overhead, lot 1) = 6 fases qui pesent sur le statut.
eq("6 fases comptees (NAZORG, MEERWERKEN et l'overhead exclus)",
   summ["started_count"], 6)

print("\n--- A346 : project_totals (le denominateur correct des heures) ---")
tot = calc.project_totals(ph)
# 661.6 h = budget des fases ENTAMEES. Le dashboard affiche aujourd'hui 736.1 h
# (toutes les fases), ce qui fait tomber le ratio sous 100% et contredit le statut.
# NB: build_phases arrondit CHAQUE fase a 1 decimale avant la somme (et Python
# arrondit 28.25 -> 28.2, arrondi bancaire) -- d'ou 668.5 et non 668.57.
eq("begroot des fases entamees = 661.6 h", tot["begroot_uren_aangesneden"], 661.6)
eq("gepresteerd sur ces memes fases = 668.5 h", tot["gepresteerd_uren"], 668.5)
eq("begroot TOUTES fases = 736.1 h (denominateur affiche aujourd'hui)",
   tot["begroot_uren_totaal"], 736.1)
ratio_correct = tot["gepresteerd_uren"] / tot["begroot_uren_aangesneden"] * 100
ratio_affiche = tot["gepresteerd_uren"] / tot["begroot_uren_totaal"] * 100
close("ratio sur fases entamees = 101.0% (coherent avec 'over budget')",
      ratio_correct, 101.0, tol=0.2)
close("ratio actuellement affiche = 90.8% (contredit le statut)",
      ratio_affiche, 90.8, tol=0.2)
eq("le ratio correct depasse 100%, l'affiche non -> c'est LA contradiction",
   (ratio_correct > 100, ratio_affiche > 100), (True, False))


# --------------------------------------------------------------------------
# 6. margin
# --------------------------------------------------------------------------
print("\n--- margin ---")
eq("marge = basis - kost", calc.margin(1000.0, 400.0), (600.0, 60))
eq("basis 0 -> pct 0, jamais de division par zero", calc.margin(0, 400.0), (-400.0, 0))
eq("None traite comme 0", calc.margin(None, None), (0.0, 0))
# A346 sur la base actuelle (gefactureerd - kost) : une marge tres negative,
# alors que Teamleader lui-meme annonce +25932.24 (price - cost).
eq("A346 marge 'gefactureerd - kost' = -26702.0",
   calc.margin(11226.54, 37928.54)[0], -26702.0)
close("A346 marge 'offerte - kost' = +25932.24 (= le champ margin de Teamleader)",
      calc.margin(63860.78, 37928.54)[0], 25932.24, tol=0.01)


# --------------------------------------------------------------------------
# 7. Cas limites — ce qui ne doit jamais lever
# --------------------------------------------------------------------------
print("\n--- cas limites ---")
eq("aucune fase -> statut 'none'", calc.project_summary([])["status"], "none")
eq("aucune fase -> totaux a zero",
   calc.project_totals([])["begroot_uren_aangesneden"], 0)
only_unbudgeted = calc.build_phases(
    [{"name": "REGIE", "budget_eur": 0.0, "spent_eur": 900.0, "tracked_hours": 10.0}], TH)
eq("que du hors-budget -> 'none', pas 'over'",
   calc.project_summary(only_unbudgeted)["status"], "none")
missing_keys = calc.build_phases([{"name": "X"}], TH)
eq("fase sans aucun champ -> pct None, pas d'exception", missing_keys[0]["pct"], None)
eq("fase sans aucun champ -> non gestart", missing_keys[0]["started"], False)
none_vals = calc.build_phases(
    [{"name": "Y", "budget_eur": None, "spent_eur": None,
      "tracked_hours": None, "budget_hours": None}], TH)
eq("valeurs None -> traitees comme 0", none_vals[0]["budget_eur"], 0)
# 'done' is inferred from a LATER phase having started -- the last phase can
# therefore never be 'done'. Locked in so a future change is deliberate.
two = calc.build_phases(
    [{"name": "1. A", "budget_eur": 100.0, "spent_eur": 50.0},
     {"name": "2. B", "budget_eur": 100.0, "spent_eur": 10.0}], TH)
eq("fase 1 'done' car la 2 a demarre", two[0]["done"], True)
eq("la derniere fase n'est jamais 'done'", two[1]["done"], False)


# --------------------------------------------------------------------------
# 8. Taxonomie des fases (lot 1) — alias, overhead, ordre
# --------------------------------------------------------------------------
print("\n--- phases.normalize / strip_number ---")
eq("'1. VOORONTWERP' -> 'voorontwerp'", phases.normalize("1. VOORONTWERP"), "voorontwerp")
eq("casse repliee : 'Voorontwerp' == '1. VOORONTWERP'",
   phases.normalize("Voorontwerp"), phases.normalize("1. VOORONTWERP"))
eq("espaces internes compresses", phases.normalize("Schets   ontwerp"), "schets ontwerp")
eq("'1) X' -> 'X'", phases.strip_number("1) X"), "X")
eq("'1 - X' -> 'X'", phases.strip_number("1 - X"), "X")
eq("sans numero : inchange", phases.strip_number("MEERWERKEN"), "MEERWERKEN")
eq("numero de tete lu", phases.leading_number("3. VOORONTWERP"), 3)
eq("pas de numero -> None", phases.leading_number("MEERWERKEN"), None)

print("\n--- phases.canonical : les demandes du client ---")
# "Schetsontwerp/haalbaarheid is eigenlijk hetzelfde als schetsontwerp"
eq("alias 'Schetsontwerp/haalbaarheid' -> schetsontwerp",
   phases.canonical("2. Schetsontwerp/haalbaarheid")["key"], "schetsontwerp")
# "Aanbestedingsdossier is hetzelfde als aanbesteding"
eq("alias 'AANBESTEDINGSDOSSIER' -> aanbesteding",
   phases.canonical("5. AANBESTEDINGSDOSSIER")["key"], "aanbesteding")
eq("meme cle que la fase cible",
   phases.canonical("Aanbestedingsdossier")["key"], phases.canonical("5. Aanbesteding")["key"])
# "Het onderdeel administratie moet niet mee opgenomen worden"
eq("administratie = overhead", phases.canonical("1. ADMINISTRATIE")["overhead"], True)
eq("voorontwerp != overhead", phases.canonical("3. VOORONTWERP")["overhead"], False)
# NON-REGRESSION: le libelle doit rester identique a l'ancien _base_of.
eq("libelle inchange vs _base_of", phases.canonical("3. VOORONTWERP")["label"], "VOORONTWERP")
eq("libelle inchange sans numero", phases.canonical("MEERWERKEN")["label"], "MEERWERKEN")
# "Kunnen de fases chronologisch staan ipv per %"
ordered = sorted(["9. BOUWCOORDINATIE", "1. ADMINISTRATIE", "3. VOORONTWERP",
                  "2. SCHETSONTWERP"], key=phases.sort_key)
eq("ordre chronologique = layout de l'offerte", ordered,
   ["1. ADMINISTRATIE", "2. SCHETSONTWERP", "3. VOORONTWERP", "9. BOUWCOORDINATIE"])
eq("fase inconnue passe apres les fases connues",
   phases.canonical("ZZZ ONBEKEND")["order"] > phases.canonical("9. BOUWCOORDINATIE")["order"],
   True)
# Une config vide ne doit jamais lever ni tout marquer overhead.
eq("taxonomie vide -> pas d'overhead",
   phases.canonical("1. ADMINISTRATIE", {})["overhead"], False)
eq("taxonomie vide -> cle quand meme normalisee",
   phases.canonical("1. ADMINISTRATIE", {})["key"], "administratie")

print("\n--- phases.suggest_aliases (bouton 'optimaliseer') ---")
sug = phases.suggest_aliases(["1. Schetsontwerp", "2. Schetsontwerp/haalbaarheid",
                              "3. Aanbesteding", "4. Aanbestedingsdossier",
                              "5. Voorontwerp"], {"aliases": {}, "order": [], "overhead": []})
eq("propose schetsontwerp/haalbaarheid -> schetsontwerp",
   sug.get("schetsontwerp/haalbaarheid"), "schetsontwerp")
eq("propose aanbestedingsdossier -> aanbesteding",
   sug.get("aanbestedingsdossier"), "aanbesteding")
eq("ne propose rien pour une fase isolee", "voorontwerp" in sug, False)
eq("aucune suggestion sur un vocabulaire deja propre",
   phases.suggest_aliases(["1. Voorontwerp", "2. Nazorg"],
                          {"aliases": {}, "order": [], "overhead": []}), {})

print("\n--- A346 : l'overhead ne doit RIEN changer ici (administratie a 48%) ---")
ph_tx = calc.build_phases(A346, TH, phases.DEFAULT_TAXONOMY)
summ_tx = calc.project_summary(ph_tx)
eq("statut toujours 'over'", summ_tx["status"], "over")
eq("toujours 2 fases en depassement", summ_tx["n_over"], 2)
eq("administratie marquee overhead dans le snapshot",
   {p["naam"]: p["overhead"] for p in ph_tx}["1. ADMINISTRATIE"], True)
# project_totals ne doit PAS exclure l'overhead : c'est du vrai travail budgete.
tot_tx = calc.project_totals(ph_tx)
eq("heures inchangees : l'overhead reste compte", tot_tx, tot)

print("\n--- le cas que le client decrit : administratie seule fait basculer ---")
ADMIN_ONLY = [
    # 249.90 EUR de budget : la premiere heure pointee fait exploser le %.
    {"name": "1. ADMINISTRATIE", "budget_eur": 249.90, "spent_eur": 700.00,
     "tracked_hours": 8.0, "budget_hours": 3.0},
    {"name": "3. VOORONTWERP", "budget_eur": 10000.0, "spent_eur": 2000.0,
     "tracked_hours": 20.0, "budget_hours": 100.0},
]
NO_TX = {"aliases": {}, "order": [], "overhead": [], "labels": {}}
eq("AVANT (taxonomie desactivee) : le projet est 'over' a cause de l'administratie",
   calc.project_summary(calc.build_phases(ADMIN_ONLY, TH, NO_TX))["status"], "over")
eq("APRES : le projet repasse 'ok'",
   calc.project_summary(calc.build_phases(ADMIN_ONLY, TH, phases.DEFAULT_TAXONOMY))["status"],
   "ok")
eq("plus aucune fase comptee en depassement",
   calc.project_summary(calc.build_phases(ADMIN_ONLY, TH, phases.DEFAULT_TAXONOMY))["n_over"],
   0)

print()
if failures:
    print(f"UNIT TESTS FAILED ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("All unit tests passed.")
