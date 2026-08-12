"""STAP 0 probe — verify what the AWP Teamleader account exposes (READ-ONLY).

Answers, against the live account through the deployed proxy:
  1. Are `cost` / `amount_billed` / `margin` filled on projects & groups?
     (null everywhere -> the 'Costs on projects' permission is OFF for the
     connected user -> the dashboard runs in fallback mode with manual rates.)
  2. Are `time_tracked` / `time_estimated` per group filled, and in seconds?
  3. What is the date field on timeTracking entries (started_on / started_at)?
  4. Verificatie-blad: for a few projects, the values the dashboard will show
     next to the raw Teamleader fields — to have AWP sign off.

Usage (PowerShell):
  $env:TL_DEV_KEY = "<DEV_API_KEY>"     # never hardcode/commit this
  python scripts/probe_costs.py

Only .list/.info calls are made. No writes, ever.
"""
import os
import sys
import json

import requests

BASE = os.environ.get("TL_PROXY_BASE",
                      "https://teamleader-onboarding-production.up.railway.app")
KEY = os.environ.get("TL_DEV_KEY")
if not KEY:
    sys.exit("TL_DEV_KEY ontbreekt. Zet eerst:  $env:TL_DEV_KEY = \"...\"")


def tl(endpoint, body=None):
    r = requests.post(f"{BASE}/api/{endpoint}", headers={"X-Dev-Key": KEY},
                      json=body or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def money(m):
    return None if not isinstance(m, dict) or m.get("amount") is None else m["amount"]


def hrs(tobj):
    if not isinstance(tobj, dict) or tobj.get("value") is None:
        return None
    return round(tobj["value"] / 3600, 2)


print(f"Proxy: {BASE}\n")
projects = [p for p in tl("projects-v2/projects.list",
                          {"page": {"size": 20, "number": 1}}).get("data", [])
            if p.get("status") == "open"][:4]
if not projects:
    sys.exit("Geen open projecten gevonden.")

any_cost = any_billed = False
date_field = None
for p in projects:
    pid = p["id"]
    info = tl("projects-v2/projects.info", {"id": pid}).get("data", {})
    print("=" * 70)
    print(f"PROJECT {info.get('title')}")
    print(f"  project-level: cost={money(info.get('cost'))} "
          f"amount_billed={money(info.get('amount_billed'))} "
          f"margin={money(info.get('margin'))} "
          f"time_tracked={hrs(info.get('time_tracked'))}u "
          f"time_estimated={hrs(info.get('time_estimated'))}u "
          f"price={money(info.get('price'))}")
    groups = tl("projects-v2/projectGroups.list",
                {"filter": {"project_id": pid}, "page": {"size": 20, "number": 1}}).get("data", [])
    tot_cost = tot_billed = 0.0
    for g in groups:
        c, b = money(g.get("cost")), money(g.get("amount_billed"))
        any_cost |= c is not None
        any_billed |= b is not None
        tot_cost += c or 0
        tot_billed += b or 0
        print(f"  group '{g.get('title')}': budget={money(g.get('external_budget'))} "
              f"spent={money(g.get('external_budget_spent'))} billed={b} cost={c} "
              f"tracked={hrs(g.get('time_tracked'))}u estimated={hrs(g.get('time_estimated'))}u")
    print(f"  Σ groups: cost={round(tot_cost,2)} billed={round(tot_billed,2)} "
          f"(vergelijk met project-level hierboven)")
    entries = tl("timeTracking.list",
                 {"filter": {"relates_to": {"type": "nextgenProject", "id": pid}},
                  "page": {"size": 3, "number": 1}}).get("data", [])
    if entries and date_field is None:
        e = entries[0]
        date_field = ("started_on" if e.get("started_on")
                      else "started_at" if e.get("started_at") else "?")
        print(f"  timeTracking entry keys: {sorted(e.keys())}")
        print(f"  -> datumveld: {date_field} = {e.get(date_field)}")

print("=" * 70)
print("\nCONCLUSIE:")
if any_cost:
    print("  cost is GEVULD -> primaire pad: kosten & marge rechtstreeks uit Teamleader. ✔")
else:
    print("  cost is overal NULL -> recht 'Kosten op projecten' staat UIT voor de")
    print("  gekoppelde gebruiker. Vraag AWP dit aan te zetten (properste oplossing),")
    print("  of vul de tarieven per persoon in via Beheer (fallback, werkt ook).")
print(f"  amount_billed {'GEVULD ✔' if any_billed else 'NULL -> gefactureerd blijft leeg tot facturen gekoppeld zijn'}")
print(f"  timeTracking datumveld: {date_field or 'geen entries gevonden'}")
