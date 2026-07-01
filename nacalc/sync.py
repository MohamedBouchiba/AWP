"""Sync engine: pull from Teamleader, compute per-project snapshots, cache in
SQLite, raise meldingen. Runs in a background thread + on a manual trigger.
The dashboard only ever reads the cache."""
import json
import re
import threading
import time

from . import config, store, teamleader as TL, calc

_trigger = threading.Event()
_thread = None
_start_lock = threading.Lock()


# ---------- parsing helpers ----------
def parse_money(s):
    if s is None:
        return None
    s = re.sub(r"[^\d,.\-]", "", str(s).strip())
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    elif "." in s:
        intp, frac = s.split(".")
        if len(frac) == 3:
            s = intp + frac
    try:
        return float(s)
    except ValueError:
        return None


def _norm(title):
    return (title or "").strip().upper()


def _resolve_mappings():
    """Map custom-field labels + work-type names to ids; cache in config."""
    cfids = {}
    for cf in TL.list_custom_field_defs():
        for key, label in config.CF_LABELS.items():
            if cf.get("label") == label:
                cfids[key] = cf.get("id")
    if cfids:
        store.set_config("custom_field_ids", cfids)
    wt = {}
    for w in TL.list_work_types():
        if w.get("name") == config.WORKTYPE_WERFBEZOEK:
            wt["werfbezoek"] = w.get("id")
        elif w.get("name") == config.WORKTYPE_BESPREKING:
            wt["bespreking"] = w.get("id")
    if wt:
        store.set_config("worktype_ids", wt)
    return {"cfids": store.get_config("custom_field_ids", {}),
            "wt": store.get_config("worktype_ids", {})}


def _quote_hours(info):
    """{normalized section title: budget hours} from the project's quotation."""
    out = {}
    qrefs = info.get("quotations") or []
    if not qrefs:
        return out
    try:
        q = TL.quotation_info(qrefs[0]["id"])
    except Exception:
        return out
    for sec in q.get("grouped_lines", []):
        section = sec.get("section")
        title = section.get("title") if isinstance(section, dict) else section
        qty = sum((li.get("quantity") or 0) for li in sec.get("line_items", []))
        if title:
            out[_norm(title)] = out.get(_norm(title), 0) + qty
    return out


def _rate_for(rates_map, uid, date):
    rows = rates_map.get(uid)            # [(effective_from, rate)] desc
    if not rows:
        return None
    for eff, rate in rows:
        if eff <= (date or "9999"):
            return rate
    return rows[-1][1]


def _is_architectuur(cfs, cfids):
    type_val = TL.cf_value(cfs, cfids.get("type"))
    type_norm = (str(type_val).strip().lower() if type_val else "")
    return type_norm not in config.NON_ARCHITECTUUR_TYPES


def _compute(item, mappings, thresholds, internal_rate):
    pid = item["id"]
    cfids, wt = mappings["cfids"], mappings["wt"]
    info = TL.project_info(pid)
    cfs = info.get("custom_fields", [])
    title = info.get("title") or item.get("title") or ""
    nr = title.split(" - ", 1)[0].strip()
    rest = title.split(" - ", 1)[1].strip() if " - " in title else ""
    werfadres = TL.cf_value(cfs, cfids.get("werfadres"))
    naam = rest or werfadres or title
    adres = werfadres if (werfadres and werfadres != naam) else ""
    categorie = TL.cf_value(cfs, cfids.get("categorie")) or ""
    contracttype = TL.cf_value(cfs, cfids.get("contracttype")) or ""
    verantw = TL.cf_value(cfs, cfids.get("verantw")) or ""
    budget_klant = parse_money(TL.cf_value(cfs, cfids.get("budget_bh")))
    raming_vo = parse_money(TL.cf_value(cfs, cfids.get("raming_awp")))
    offerte = TL.amount(info.get("price")) or TL.amount(info.get("calculated_price"))

    is_arch = _is_architectuur(cfs, cfids)

    groups = TL.project_groups(pid)
    qh = _quote_hours(info)
    raw = [{"name": g.get("title"),
            "budget_eur": TL.amount(g.get("external_budget")),
            "spent_eur": TL.amount(g.get("external_budget_spent")),
            "budget_hours": qh.get(_norm(g.get("title")), 0)} for g in groups]
    phases = calc.build_phases(raw, thresholds)
    summary = calc.project_summary(phases)

    entries = TL.project_time_entries(pid)
    werfbezoeken = sum(1 for e in entries
                       if (e.get("work_type") or {}).get("id") == wt.get("werfbezoek"))
    besprekingen = sum(1 for e in entries
                       if (e.get("work_type") or {}).get("id") == wt.get("bespreking"))

    # Real tracked hours (Teamleader time tracking) -- single source of truth for hours,
    # consistent with the cost. Budget hours = the project's own Teamleader time budget.
    total_tracked_h = sum((e.get("duration") or 0) for e in entries) / 3600
    uren_gepresteerd = round(total_tracked_h, 1)
    uren_begroot = TL.hours(info.get("time_estimated"))
    kost = round(total_tracked_h * internal_rate, 2)
    # Margin = AWP quote − effective cost (can be NEGATIVE = over the quoted budget).
    # No quote in Teamleader -> we can't judge the margin, so leave it blank ("—").
    if offerte and offerte > 0:
        marge, marge_pct = calc.margin(offerte, kost)
    else:
        marge, marge_pct = None, None
    cost_estimated = 0

    worst = None
    for p in phases:
        if p["started"] and p["color"] in ("red", "darkred"):
            if worst is None or (p["pct"] or 0) > (worst["pct"] or 0):
                worst = p
    attention = worst["naam"] if worst else ""

    return {
        "project_id": pid, "project_key": nr, "titel": title, "naam": naam, "adres": adres,
        "status": info.get("status"), "is_architectuur": 1 if is_arch else 0,
        "categorie": categorie, "contracttype": contracttype, "verantw_arch": verantw,
        "verantw_medewerker": "", "budget_klant": budget_klant, "offerte_awp": offerte,
        "raming_vo": raming_vo, "uren_begroot": uren_begroot,
        "uren_gepresteerd": uren_gepresteerd, "effectieve_kost": kost,
        "marge": marge, "marge_pct": marge_pct, "summary_status": summary["status"],
        "n_over": summary["n_over"], "n_warn": summary["n_warn"],
        "cost_estimated": cost_estimated, "werfbezoeken": werfbezoeken,
        "besprekingen": besprekingen, "attention_note": attention,
        "phases_json": json.dumps(phases), "synced_at": store.now_iso(),
    }


def _make_meldingen(snap):
    pid = snap["project_id"]
    store.clear_meldingen_for(pid)
    for p in json.loads(snap["phases_json"]):
        if p["started"] and p["color"] in ("amber", "red", "darkred"):
            sev = p["color"]
            store.upsert_melding(pid, snap["project_key"], snap["naam"], p["naam"],
                                 sev, p["pct"], p["naam"])


def run_full():
    if store.get_sync_state().get("running"):
        return
    store.set_sync_state(running=1, last_run_at=store.now_iso(), last_error=None)
    count = 0
    try:
        mappings = _resolve_mappings()
        thresholds = store.get_config("thresholds", config.DEFAULT_THRESHOLDS)
        internal_rate = store.get_config("internal_cost_rate", config.DEFAULT_INTERNAL_COST_RATE)
        items = TL.tl_all("projects-v2/projects.list", {}, size=20)
        seen = []
        for item in items:
            if item.get("status") != "open":
                continue
            try:
                snap = _compute(item, mappings, thresholds, internal_rate)
            except Exception:
                continue
            store.upsert_snapshot(snap)
            _make_meldingen(snap)
            seen.append(snap["project_id"])
            count += 1
            time.sleep(0.3)
        store.delete_snapshots_except(seen)
        store.set_sync_state(last_ok_at=store.now_iso(), projects_synced=count)
    except Exception as e:
        store.set_sync_state(last_error=str(e)[:300])
    finally:
        store.set_sync_state(running=0)


def trigger_sync():
    _trigger.set()


def _loop():
    # initial run only if cache empty (avoid hammering on every redeploy)
    try:
        if not store.list_snapshots(architectuur_only=False):
            run_full()
    except Exception:
        pass
    while True:
        interval = store.get_config("sync_interval_minutes", config.DEFAULT_SYNC_INTERVAL_MINUTES)
        fired = _trigger.wait(timeout=max(60, int(interval) * 60))
        _trigger.clear()
        run_full()


def start_background():
    global _thread
    with _start_lock:
        if _thread and _thread.is_alive():
            return
        _thread = threading.Thread(target=_loop, name="nacalc-sync", daemon=True)
        _thread.start()
