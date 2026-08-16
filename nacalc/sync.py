"""Sync engine: pull from Teamleader, compute per-project snapshots, cache in
SQLite, raise meldingen. Runs in a background thread + on a manual trigger.
The dashboard only ever reads the cache."""
import calendar
import json
import os
import re
import threading
import time

from . import config, store, teamleader as TL, calc, mailer, phases as phases_mod

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


def _compute(item, mappings, thresholds, internal_rate, rates_map, taxonomy=None,
             basis=calc.DEFAULT_BASIS):
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
    project_type = str(TL.cf_value(cfs, cfids.get("type")) or "").strip()

    is_arch = _is_architectuur(cfs, cfids)

    groups = TL.project_groups(pid)
    qh = _quote_hours(info)
    raw = [{"name": g.get("title"),
            "budget_eur": TL.amount(g.get("external_budget")),
            "spent_eur": TL.amount(g.get("external_budget_spent")),
            # Real per-phase figures from the group itself; null when the
            # 'Costs on projects' permission hides them (amount_or_none).
            "billed_eur": TL.amount_or_none(g.get("amount_billed")),
            "cost_eur": TL.amount_or_none(g.get("cost")),
            "tracked_hours": TL.hours(g.get("time_tracked")),
            # Budgeted hours on the group; quotation section hours as fallback.
            "budget_hours": TL.hours(g.get("time_estimated")) or qh.get(_norm(g.get("title")), 0)}
           for g in groups]
    phases = calc.build_phases(raw, thresholds, taxonomy, basis, internal_rate)
    summary = calc.project_summary(phases, thresholds)
    totals = calc.project_totals(phases)

    entries = TL.project_time_entries(pid)
    werfbezoeken = sum(1 for e in entries
                       if (e.get("work_type") or {}).get("id") == wt.get("werfbezoek"))
    besprekingen = sum(1 for e in entries
                       if (e.get("work_type") or {}).get("id") == wt.get("bespreking"))

    def _edate(e):
        return str(e.get("started_on") or e.get("started_at") or "")

    # Distinct activity months (YYYY-MM) -> analyse period filter.
    months = sorted({_edate(e)[:7] for e in entries if _edate(e)})

    total_tracked_h = sum((e.get("duration") or 0) for e in entries) / 3600
    uren_gepresteerd = round(total_tracked_h, 1)
    # Budget hours: sum over the groups (project.time_estimated is usually 0).
    uren_begroot = round(sum(p["budget_hours"] for p in phases), 1) or TL.hours(info.get("time_estimated"))

    # Hours per person (always available); cost per person ONLY when we know a
    # rate -- Teamleader's API never exposes cost per user, just the total.
    by_user = {}
    for e in entries:
        uid = (e.get("user") or {}).get("id")
        h = (e.get("duration") or 0) / 3600
        d = by_user.setdefault(uid, {"uid": uid, "hours": 0.0, "cost": 0.0, "rated": False})
        d["hours"] += h
        rate = _rate_for(rates_map, uid, _edate(e)[:10])
        if rate is not None:
            d["cost"] += h * rate
            d["rated"] = True
    per_person = sorted(
        ({"uid": d["uid"], "hours": round(d["hours"], 1),
          "cost": round(d["cost"], 2) if d["rated"] else None} for d in by_user.values()),
        key=lambda d: -d["hours"])

    # Effective cost — auto-detected source:
    #  1) Teamleader's real cost (per person, historical rates) when the
    #     'Costs on projects' permission exposes it (project, else Σ groups);
    #  2) manual per-person rates (Beheer cost_rates table, with history);
    #  3) last resort: flat internal rate (legacy behavior).
    kost = TL.amount_or_none(info.get("cost"))
    if kost is None:
        # ONLY groups whose cost really came from Teamleader. build_phases now
        # fills cost_eur with an hours x rate estimate when the permission is
        # off, and summing those here would report an estimate as a real cost.
        group_costs = [p["cost_eur"] for p in phases
                       if p.get("cost_eur") is not None and p.get("kost_bron") == "teamleader"]
        kost = round(sum(group_costs), 2) if group_costs else None
    cost_estimated = 0
    kost_bron = "teamleader"
    if kost is None:
        cost_estimated = 1
        kost = 0.0
        any_flat = False
        for e in entries:
            h = (e.get("duration") or 0) / 3600
            uid = (e.get("user") or {}).get("id")
            rate = _rate_for(rates_map, uid, _edate(e)[:10])
            if rate is None:
                any_flat = True
            kost += h * (rate if rate is not None else internal_rate)
        kost = round(kost, 2)
        # No entries -> no rate was applied at all; claiming "rates" would be a lie.
        kost_bron = None if not entries else ("flat" if any_flat else "rates")

    # Invoiced (gefactureerd): Teamleader amount_billed — project level, else Σ groups.
    # Stays None when NO billing data is exposed at all (permission off), so the
    # UI shows "—" instead of a fake real €0 (mirrors the cost-path handling).
    gefactureerd = TL.amount_or_none(info.get("amount_billed"))
    if gefactureerd is None:
        billed = [p["billed_eur"] for p in phases if p.get("billed_eur") is not None]
        gefactureerd = round(sum(billed), 2) if billed else None

    # Margin = invoiced − effective cost (feedback ronde 2). Nothing invoiced
    # yet -> "—" (None), to avoid a huge fake negative on running projects.
    if gefactureerd and gefactureerd > 0:
        marge, marge_pct = calc.margin(gefactureerd, kost)
    else:
        marge, marge_pct = None, None

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
        # Hours restricted to the phases actually STARTED. Comparing all hours
        # worked against the budget of every phase -- including ones nobody has
        # touched -- is what made A346 read "93% of hours" while two phases were
        # genuinely over budget. See calc.project_totals().
        "uren_begroot_gestart": totals["begroot_uren_aangesneden"],
        "uren_gepresteerd_gestart": totals["gepresteerd_uren"],
        "gefactureerd": gefactureerd, "project_type": project_type,
        "activity_json": json.dumps(months),
        "uren_per_persoon_json": json.dumps(per_person), "kost_bron": kost_bron,
        "marge": marge, "marge_pct": marge_pct, "summary_status": summary["status"],
        "n_over": summary["n_over"], "n_warn": summary["n_warn"],
        "cost_estimated": cost_estimated, "werfbezoeken": werfbezoeken,
        "besprekingen": besprekingen, "attention_note": attention,
        "phases_json": json.dumps(phases), "synced_at": store.now_iso(),
    }


def _alertable(phases):
    """Phases that can raise an alert: started, quoted, with a time budget, and
    not overhead. Same exclusions as the project badge, so the Meldingen page can
    never nag about exactly what the status ignores."""
    return [p for p in phases
            if p.get("started") and p.get("applicable") and not p.get("overhead")
            and (p.get("budget_hours") or 0) > 0]


def _crossed(pct, levels):
    """[(key, threshold)] for every threshold `pct` has reached, low to high."""
    return [(k, v) for k, v in levels if pct is not None and pct >= v]


def _make_meldingen(snap, thresholds=None, project_thresholds=None):
    """One alert per THRESHOLD CROSSED, created once and kept while it holds.

    Client rule: "Per fase worden maximaal drie meldingen gegenereerd, elk exact
    één keer. Zolang dezelfde drempel overschreden blijft, komt er geen nieuwe
    melding of mail. Pas bij het bereiken van een volgende drempel volgt een
    nieuwe melding." So a phase at 120% carries three alerts (80, 100, 115), not
    one for its current colour band.

    Alerts whose threshold is no longer crossed are pruned; the ones that hold
    keep their seen / notified / handled state through upsert_melding.
    """
    th = thresholds or config.DEFAULT_THRESHOLDS
    pth = project_thresholds or config.DEFAULT_PROJECT_THRESHOLDS
    # amber/red/darkred double as the three phase levels: they ARE the colour
    # thresholds the client already tunes in Beheer.
    levels = [("amber", th.get("amber", 80)), ("red", th.get("red", 100)),
              ("darkred", th.get("darkred", 115))]
    pid, key, naam = snap["project_id"], snap["project_key"], snap["naam"]
    verantw = snap.get("verantw_arch")
    phases = json.loads(snap["phases_json"] or "[]")
    keep = set()

    for p in _alertable(phases):
        for sev, _drempel in _crossed(p.get("uren_pct"), levels):
            store.upsert_melding(pid, key, naam, p["naam"], sev, p["uren_pct"],
                                 verantw=verantw, soort="fase",
                                 uren=p.get("tracked_hours"),
                                 uren_budget=p.get("budget_hours"))
            keep.add((p["naam"], sev))

    # Project level: the cumulative hours over ALL phases, including the ones
    # not started. That denominator is the point -- "vroeg zien dat een project
    # al 80% van zijn totale urenbudget verbruikt heeft terwijl er nog fases
    # moeten komen" is unsayable if you only count the phases already running.
    budg = sum(p.get("budget_hours") or 0 for p in phases
               if not p.get("overhead") and (p.get("budget_hours") or 0) > 0)
    trak = sum(p.get("tracked_hours") or 0 for p in phases
               if not p.get("overhead") and (p.get("budget_hours") or 0) > 0)
    if budg > 0:
        pct = round(trak / budg * 100, 1)
        for _k, drempel in _crossed(pct, [(f"p{d}", d) for d in pth]):
            sev = f"p{int(drempel)}"
            store.upsert_melding(pid, key, naam, "", sev, pct,
                                 verantw=verantw, soort="project",
                                 uren=round(trak, 1), uren_budget=round(budg, 1))
            keep.add(("", sev))

    store.prune_meldingen(pid, keep)


def _digest_body(lang, rows):
    lines = []
    cur = None
    for m in rows:
        key = f'{m["project_key"] or ""} · {m["naam"] or ""}'
        if key != cur:
            lines.append(f"\n{key}")
            cur = key
        state = "OVER BUDGET" if m["severity"] in ("red", "darkred") else "dreigt over"
        lines.append(f"   - {m['phase_naam']}: {state} ({m['pct']}%)")
    return "\n".join(lines).strip()


def send_digests(now_iso_str=None):
    """One digest per responsible, at most once a day. Returns #mails sent.

    The client's constraint was explicit: "wel geen spam per tijdregistratie,
    dus er moet een manier zijn om deze mailing te dempen als er een analyse van
    het budget/timing is gebeurd." Three independent guards:
      1. an alert is mailed exactly once, ever (notified_at, written to the DB
         right after a successful send);
      2. alerts are grouped into a single mail per responsible, so a project
         with eight drifting phases is one message, not eight;
      3. handled alerts leave the list and are never re-sent.
    """
    if not mailer.is_configured():
        return 0
    now = now_iso_str or store.now_iso()
    rows = store.meldingen_to_notify()
    if not rows:
        return 0
    emails = {k.strip().lower(): v for k, v in
              (store.get_config("verantw_emails", {}) or {}).items()}

    by_person = {}
    for m in rows:
        addr = emails.get((m.get("verantw") or "").strip().lower())
        if not addr:
            continue          # nobody to send to -> leave notified_at untouched
        by_person.setdefault(addr, []).append(m)

    sent = 0
    for addr, items in by_person.items():
        body = (f"{_digest_body('nl', items)}\n\n"
                f"Details: {os.environ.get('APP_URL', 'https://awp-dashboard.up.railway.app')}/app/meldingen\n")
        subject = f"[AWP nacalculatie] {len(items)} fase(s) over of dreigend over budget"
        ok, _detail = mailer.send(addr, subject, body)
        if ok:
            # Marked immediately: a crash further down must never cause a second
            # mail about the same alerts.
            store.mark_notified([m["id"] for m in items], now)
            sent += 1
    return sent


def _age_minutes(iso):
    """Minutes since an ISO stamp written by store.now_iso(), or None.

    calendar.timegm, not time.mktime: the stamps are UTC (store.now_iso uses
    gmtime) while mktime reads a struct_time as LOCAL time, which put the age
    an hour or two out depending on daylight saving.
    """
    try:
        return (time.time() - calendar.timegm(
            time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))) / 60
    except (TypeError, ValueError):
        return None


# A run cannot legitimately last this long: gunicorn is pinned to one worker, so
# anything older is a corpse left by a killed process, not a live sync.
STALE_RUN_MINUTES = 45


def run_full():
    st = store.get_sync_state()
    if st.get("running"):
        age = _age_minutes(st.get("last_run_at") or "")
        if age is None or age < STALE_RUN_MINUTES:
            return
        # Second line of defence behind the boot-time reset in store.init_db():
        # without it a single killed process froze the cache permanently, since
        # every later call returned right here.
        store.set_sync_state(last_error="vorige sync afgebroken — opnieuw gestart")
    store.set_sync_state(running=1, last_run_at=store.now_iso(), last_error=None)
    count = 0
    try:
        mappings = _resolve_mappings()
        try:
            # Cache the Teamleader users for the Beheer per-person rates form
            # (pages never call the API themselves).
            store.set_config("tl_users", [
                {"id": u.get("id"),
                 "name": (" ".join(x for x in [u.get("first_name") or "",
                                               u.get("last_name") or ""] if x)
                          or u.get("email") or u.get("id"))}
                for u in TL.list_users()])
        except Exception:
            pass
        thresholds = store.get_config("thresholds", config.DEFAULT_THRESHOLDS)
        internal_rate = store.get_config("internal_cost_rate", config.DEFAULT_INTERNAL_COST_RATE)
        taxonomy = store.get_config("phase_taxonomy", phases_mod.DEFAULT_TAXONOMY)
        basis = store.get_config("status_basis", calc.DEFAULT_BASIS)
        project_thresholds = store.get_config("project_thresholds",
                                              config.DEFAULT_PROJECT_THRESHOLDS)
        rates_map = store.cost_rate_map()
        seen_phase_names = set()   # feeds the Beheer "optimaliseer fasenamen" button
        items = TL.tl_all("projects-v2/projects.list", {}, size=20)
        seen = []
        saw_tl_costs = False
        failed = 0
        for item in items:
            # Closed projects used to be skipped here, and delete_snapshots_except
            # then wiped them from the cache -- so a finished project, the one
            # whose margin is finally definitive, disappeared for good. They are
            # ingested now. Today this changes nothing (187/187 AWP projects are
            # `open`; filter.status=["closed"] returns zero), but the day AWP
            # starts closing them the history survives.
            try:
                snap = _compute(item, mappings, thresholds, internal_rate, rates_map,
                                taxonomy, basis)
            except Exception:
                failed += 1      # transient API error on one project
                continue
            store.upsert_snapshot(snap)
            _make_meldingen(snap, thresholds, project_thresholds)
            seen.append(snap["project_id"])
            seen_phase_names.update(p["naam"] for p in json.loads(snap["phases_json"])
                                    if p.get("naam"))
            if not snap["cost_estimated"]:
                saw_tl_costs = True
            count += 1
            time.sleep(0.3)
        if count:
            # Auto-detected: True when Teamleader exposed real costs (the
            # 'Costs on projects' permission is on for the connected user).
            store.set_config("has_project_costs", saw_tl_costs)
            # The raw phase vocabulary, so Beheer can propose alias merges and a
            # chronological order without anyone re-reading the xlsx export.
            store.set_config("seen_phase_names", sorted(seen_phase_names))
        if failed:
            # A project we couldn't compute is NOT gone from Teamleader. Pruning
            # here would delete a live project (and, if every call failed, wipe
            # the whole cache). Leave the old rows and retry next run.
            store.set_sync_state(last_error=f"{failed} project(s) failed to sync")
        else:
            store.delete_snapshots_except(seen)
            # Clean run only: every snapshot now has the current shape, so the
            # boot self-heal (_loop) won't re-sync on the next deploy. A partial
            # run leaves data_version stale on purpose -> it retries.
            store.set_config("data_version", config.CURRENT_DATA_VERSION)
        store.set_sync_state(last_ok_at=store.now_iso(), projects_synced=count)
        try:
            # After the cache is consistent, never during. Isolated: a mail
            # problem must not mark the whole sync as failed.
            send_digests()
        except Exception:
            pass
    except Exception as e:
        store.set_sync_state(last_error=str(e)[:300])
    finally:
        store.set_sync_state(running=0)


def trigger_sync():
    _trigger.set()


def _loop():
    # Initial run only when there is something to fix (avoid hammering the API
    # on every redeploy):
    #  - empty cache, or
    #  - cache written by an older _compute (data_version) -> one self-heal sync,
    #    so stale rows never show up under new labels. data_version lives on the
    #    persistent volume and is bumped only after a successful run, so this
    #    fires once; a failed heal simply retries on the next boot/interval.
    try:
        if not store.list_snapshots(architectuur_only=False):
            run_full()
        elif store.get_config("data_version", 0) != config.CURRENT_DATA_VERSION:
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
