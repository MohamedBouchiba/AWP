"""Routes/pages for the nacalculatie dashboard (blueprint 'nacalc')."""
import json
import re
import time

from flask import (Blueprint, request, redirect, session, jsonify, make_response)

from . import store, auth, sync, config, calc, phases as phases_mod
from .ui import pages, components
from .i18n import t, pick_lang

bp = Blueprint("nacalc", __name__)


def get_lang():
    c = request.cookies.get("lang")
    if c in ("nl", "en"):
        return c
    u = auth.current_user()
    if u and u.get("lang") in ("nl", "en"):
        return u["lang"]
    return "nl"


def render_page(active, title, sub, content):
    lang = get_lang()
    u = auth.current_user()
    ss = store.get_sync_state()
    if ss.get("last_ok_at"):
        synced = f"{t('synced', lang)} · {ss['last_ok_at'][11:16]}"
    else:
        synced = t("never_synced", lang)
    badge = store.count_unseen_meldingen()
    collapsed = request.cookies.get("sidebar") == "collapsed"
    return pages.shell(lang, active, title, sub, content, badge, synced,
                           ss.get("running"), bool(u and u["is_admin"]), collapsed)


# ---------- auth ----------
@bp.route("/app/login", methods=["GET", "POST"])
def login():
    lang = pick_lang(request.args.get("lang") or get_lang())
    if request.method == "POST":
        u = store.get_user_by_email(request.form.get("email", ""))
        if u and auth.verify_password(request.form.get("password", ""), u["password_hash"]):
            session["uid"] = u["id"]
            return redirect(request.args.get("next") or "/app")
        return pages.login_page(lang, error=True), 401
    return pages.login_page(lang, error=False)


@bp.get("/app/logout")
def logout():
    session.clear()
    return redirect("/app/login")


@bp.get("/app/lang/<code>")
def set_lang(code):
    lang = pick_lang(code)
    u = auth.current_user()
    if u:
        store.set_user_lang(u["id"], lang)
    resp = make_response(redirect(request.referrer or "/app"))
    resp.set_cookie("lang", lang, max_age=31536000, samesite="Lax")
    return resp


# ---------- overzicht ----------
@bp.get("/app")
@bp.get("/app/overzicht")
@auth.login_required
def overzicht():
    lang = get_lang()
    all_snaps = store.list_snapshots(architectuur_only=True)
    # Server-side selection (period + owner), so the KPI cards follow it. The
    # search/categorie/contract/status controls stay client-side as before.
    period, d_from, d_to, _ = _filter_args()
    verantw = (request.args.get("verantw") or "").strip()
    snaps = _select_snapshots(all_snaps, period, d_from, d_to, [])
    if verantw:
        snaps = [s for s in snaps if (s.get("verantw_arch") or "") == verantw]
    over = sum(1 for s in snaps if s["summary_status"] == "over")
    warn = sum(1 for s in snaps if s["summary_status"] == "warn")
    # Only invoiced projects contribute a margin (components.visible_marge is the
    # single gate) -- a stale pre-sync row must not inflate this KPI.
    tot_marge = sum(m for s in snaps
                    if (m := components.visible_marge(s)) is not None)
    kpis = [
        {"lab": t("kpi_running", lang), "val": len(snaps), "meta": t("kpi_meta_arch", lang), "cls": ""},
        {"lab": t("kpi_over", lang), "val": over, "meta": t("kpi_meta_action", lang) if over else t("kpi_meta_ok", lang), "cls": "up" if over else "ok"},
        {"lab": t("kpi_warn", lang), "val": warn, "meta": t("kpi_meta_warn", lang), "cls": "up" if warn else ""},
        {"lab": t("kpi_margin", lang), "val": components.eur(tot_marge), "meta": t("kpi_meta_margin", lang), "cls": "ok" if tot_marge >= 0 else "up"},
    ]
    # Dropdown options come from ALL projects, never from the current selection,
    # so filtering can't make the option you want disappear.
    cats = sorted({s["categorie"] for s in all_snaps if s["categorie"]})
    cons = sorted({s["contracttype"] for s in all_snaps if s["contracttype"]})
    verantws = sorted({s["verantw_arch"] for s in all_snaps if s["verantw_arch"]})
    ss = store.get_sync_state()
    fstate = {"period": period, "verantw": verantw,
              "n_sel": len(snaps), "n_all": len(all_snaps)}
    content = pages.render_overzicht(lang, snaps, kpis, cats, cons,
                                         syncing=bool(ss.get("running")), show_rates_banner=False,
                                         verantws=verantws, fstate=fstate)
    return render_page("overzicht", t("ov_title", lang), t("ov_sub", lang), content)


@bp.get("/app/project/<pid>")
@auth.login_required
def project_detail(pid):
    s = store.get_snapshot(pid)
    if not s:
        return "", 404
    u = auth.current_user()
    # Names come from the cached tl_users config (written by the sync thread) --
    # pages never call the Teamleader API.
    names = {x.get("id"): x.get("name") for x in store.get_config("tl_users", [])}
    idle = store.get_config("afgerond_maanden", config.DEFAULT_AFGEROND_MAANDEN)
    return pages.render_drawer(get_lang(), s, is_admin=bool(u and u["is_admin"]),
                               user_names=names, afgerond=is_afgerond(s, months_idle=idle),
                               afgerond_maanden=idle)


@bp.post("/app/project/<pid>/gefactureerd")
@auth.admin_required
def set_manual_invoiced(pid):
    """Invoices sent outside Teamleader, typed in by an admin.

    A plain form POST, not fetch: the drawer is injected as raw HTML, so a
    <script> inside it would never execute. Redirects back to the overview,
    where the new margin is visible immediately (visible_marge derives it).
    """
    raw = (request.form.get("bedrag") or "").strip()
    try:
        bedrag = float(raw.replace(",", ".")) if raw else None
    except ValueError:
        bedrag = None
    store.set_manual_invoiced(pid, bedrag)
    return redirect(request.referrer or "/app")


@bp.post("/app/project/<pid>/afgerond")
@auth.admin_required
def set_afgerond(pid):
    """Force a project's finished/running state, or hand it back to the rule."""
    v = request.form.get("afgerond")
    store.set_afgerond_manueel(pid, None if v not in ("0", "1") else int(v))
    return redirect(request.referrer or "/app")


# ---------- meldingen ----------
@bp.get("/app/meldingen")
@auth.login_required
def meldingen():
    lang = get_lang()
    items = store.list_meldingen()
    store.mark_meldingen_seen()
    content = pages.render_meldingen(lang, items)
    return render_page("meldingen", t("nav_meldingen", lang), t("ml_sub", lang), content)


# ---------- analyse ----------
def _months_last(n):
    """Rolling window: the current month plus the n previous ones ('YYYY-MM').
    'Last month' early in a new month would otherwise match almost nothing."""
    tm = time.gmtime()
    y, m = tm.tm_year, tm.tm_mon
    out = set()
    for _ in range(n + 1):
        out.add(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def _months_range(a, b):
    """Inclusive set of 'YYYY-MM' between a and b. Iterates DOWN from b so the
    240-month safety cap drops the oldest months, never the recent ones."""
    try:
        ya, ma = int(a[:4]), int(a[5:7])
        yb, mb = int(b[:4]), int(b[5:7])
    except (ValueError, TypeError):
        return set()
    out = set()
    while (yb, mb) >= (ya, ma) and len(out) < 240:
        out.add(f"{yb:04d}-{mb:02d}")
        mb -= 1
        if mb == 0:
            yb, mb = yb - 1, 12
    return out


def _taxonomy():
    return store.get_config("phase_taxonomy", phases_mod.DEFAULT_TAXONOMY)


def is_afgerond(s, now_ym=None, months_idle=None):
    """Is this project finished?

    Teamleader would be the natural source, but AWP keeps every project `open`
    (187/187; filter.status=["closed"] returns nothing), so the automatic rule is
    inactivity. Precedence, most authoritative first:
      1. an explicit manual override set in the drawer
      2. Teamleader's own status, the day AWP starts closing projects
      3. no hour booked for `months_idle` months
    """
    man = s.get("afgerond_manueel")
    if man is not None:
        return bool(man)
    if (s.get("status") or "").strip().lower() == "closed":
        return True
    if months_idle is None:
        months_idle = store.get_config("afgerond_maanden", config.DEFAULT_AFGEROND_MAANDEN)
    months = json.loads(s.get("activity_json") or "[]")
    return calc.afgerond_from_activity(max(months) if months else None,
                                       now_ym or time.strftime("%Y-%m", time.gmtime()),
                                       int(months_idle))


def _select_dossier(snaps, dossier):
    """'lopend' / 'afgerond' / anything else = no filter."""
    if dossier not in ("lopend", "afgerond"):
        return snaps
    now_ym = time.strftime("%Y-%m", time.gmtime())
    idle = store.get_config("afgerond_maanden", config.DEFAULT_AFGEROND_MAANDEN)
    want = (dossier == "afgerond")
    return [s for s in snaps if is_afgerond(s, now_ym, idle) == want]


def _filter_args():
    """The analyse filter, read once. Shared by the page and the export."""
    return (request.args.get("period") or "",
            request.args.get("from") or "",
            request.args.get("to") or "",
            [p for p in request.args.getlist("pids") if p])


def _dossier_arg():
    """'' | 'lopend' | 'afgerond' — orthogonal to the period/project selection."""
    d = request.args.get("dossier") or ""
    return d if d in ("lopend", "afgerond") else ""


def _select_snapshots(snaps, period, d_from, d_to, pids):
    """Pick the projects the graphs/export run on.

    The three filters are MUTUALLY EXCLUSIVE; exactly one branch fires, in this
    documented precedence (the UI mirrors it by clearing the others):
      1. an explicit project selection
      2. a rolling period (1/3/6/12 months)
      3. a custom from-to range
      4. otherwise: everything
    A project matches a period when time was logged in one of those months
    (activity_json, filled at sync). Once selected, its FULL figures are used --
    numbers are never sliced by date (per the feedback spec).
    """
    if pids:
        wanted = set(pids)
        return [s for s in snaps if s["project_id"] in wanted]
    if period in ("1", "3", "6", "12"):
        months = _months_last(int(period))
    elif period == "custom" and (d_from or d_to):
        months = _months_range(d_from or "2000-01",
                               d_to or time.strftime("%Y-%m", time.gmtime()))
    else:
        return list(snaps)
    return [s for s in snaps if months & set(json.loads(s.get("activity_json") or "[]"))]


def _aggregate_phases(sel, taxonomy=None):
    """Per CANONICAL phase, over the selection.

    Grouping goes through phases.canonical() rather than a bare number-strip, so
    legacy quote wording collapses ('Schetsontwerp/haalbaarheid' ==
    'Schetsontwerp', 'Aanbestedingsdossier' == 'Aanbesteding') and casing no
    longer splits a phase in two. Resolved LIVE from the name, so an alias saved
    in Beheer applies immediately and pre-taxonomy snapshots group correctly too.

    Sums are kept over MATCHED instance sets -- budget only counts where the
    instance also has billing data, and margin only where billed AND cost exist --
    otherwise old-shape rows (no billed_eur/cost_eur keys) would bias the ratios.
    """
    agg = {}
    for s in sel:
        for p in json.loads(s["phases_json"] or "[]"):
            c = phases_mod.canonical(p.get("naam"), taxonomy)
            d = agg.setdefault(c["key"], {
                "label": c["label"], "order": c["order"],
                "billed": 0.0, "budget_b": 0.0, "n_billed": 0,
                "tracked": 0.0, "budget_h": 0.0,
                "m3": 0.0, "billed3": 0.0, "cost3": 0.0, "n_m3": 0,
                "n": 0, "started_hours": []})
            d["n"] += 1
            d["tracked"] += p.get("tracked_hours") or 0
            d["budget_h"] += p.get("budget_hours") or 0
            billed, cost = p.get("billed_eur"), p.get("cost_eur")
            if billed is not None:
                d["billed"] += billed
                d["budget_b"] += p.get("budget_eur") or 0
                d["n_billed"] += 1
            if billed is not None and cost is not None:
                d["m3"] += billed - cost
                d["billed3"] += billed
                d["cost3"] += cost
                d["n_m3"] += 1
            if p.get("started"):
                d["started_hours"].append(p.get("tracked_hours") or 0)
    return agg


def _profit_by(sel, key):
    """Invoiced - effective cost, grouped by a snapshot column (categorie /
    contracttype). Projects with nothing invoiced are skipped via the SAME gate
    the margin uses (components.invoiced) -- otherwise running projects show fake
    big losses, and a negative net would be included here but blank elsewhere."""
    by = {}
    for s in sel:
        k = (s.get(key) or "").strip()
        kost = s.get("effectieve_kost")
        if not k or not components.invoiced(s) or kost is None:
            continue
        d = by.setdefault(k, {"billed": 0.0, "cost": 0.0, "n": 0})
        d["billed"] += components.invoiced_total(s)   # incl. invoices sent outside TL
        d["cost"] += kost
        d["n"] += 1
    return sorted(((k, round(d["billed"] - d["cost"], 2), round(d["billed"], 2),
                    round(d["cost"], 2), d["n"]) for k, d in by.items()),
                  key=lambda x: x[1])


@bp.get("/app/analyse")
@auth.login_required
def analyse():
    lang = get_lang()
    snaps = store.list_snapshots(architectuur_only=True)
    period, d_from, d_to, pids = _filter_args()
    dossier = _dossier_arg()
    sel = _select_dossier(_select_snapshots(snaps, period, d_from, d_to, pids), dossier)
    agg = _aggregate_phases(sel, _taxonomy())

    # 1) Invoiced € vs quote budget € per phase (delta% above/below budget).
    g1 = sorted(((d["label"], round(d["billed"], 2), round(d["budget_b"], 2),
                  round(d["billed"] / d["budget_b"] * 100 - 100), d["n_billed"])
                 for d in agg.values() if d["budget_b"] > 0 and d["n_billed"]),
                key=lambda x: -x[3])
    # 2) Tracked vs budgeted hours per phase.
    g2 = sorted(((d["label"], round(d["tracked"], 1), round(d["budget_h"], 1),
                  round(d["tracked"] / d["budget_h"] * 100), d["n"])
                 for d in agg.values() if d["budget_h"] > 0),
                key=lambda x: -x[3])
    # 3) Profitability per phase: invoiced − effective cost (€), paired instances only.
    g3 = sorted(((d["label"], round(d["m3"], 2), round(d["billed3"], 2),
                  round(d["cost3"], 2), d["n_m3"])
                 for d in agg.values() if d["n_m3"]),
                key=lambda x: x[1])
    # 4) Profitability per CATEGORY (client: "type is actually categorie").
    g4 = _profit_by(sel, "categorie")
    # 6) Profitability per contract type.
    g6 = _profit_by(sel, "contracttype")
    # 5) Average tracked hours per started phase.
    g5 = sorted(((d["label"], round(sum(d["started_hours"]) / len(d["started_hours"]), 1),
                  len(d["started_hours"]))
                 for d in agg.values() if d["started_hours"]),
                key=lambda x: -x[1])

    fstate = {"period": period, "from": d_from, "to": d_to, "pids": pids,
              "dossier": dossier,
              "projects": [(s["project_id"], f'{s["project_key"] or ""} · {s["naam"] or ""}')
                           for s in snaps],
              "n_sel": len(sel)}
    content = pages.render_analyse(lang, g1, g2, g3, g4, g5, g6, fstate)
    return render_page("analyse", t("nav_analyse", lang), t("an_sub", lang), content)


@bp.get("/app/analyse/export")
@auth.login_required
def analyse_export():
    """Excel export of the data behind the graphs, for the ACTIVE filter.

    Two sheets: 'Projecten' (basis of graphs 4 & 6) and 'Fases' (basis of 1,2,3,5).
    Deliberately contains NO per-person data, so it needs no admin gate.
    """
    from io import BytesIO
    from openpyxl import Workbook
    from flask import send_file

    snaps = store.list_snapshots(architectuur_only=True)
    sel = _select_dossier(_select_snapshots(snaps, *_filter_args()), _dossier_arg())
    xs = components.xl_safe   # neutralise spreadsheet formula injection

    wb = Workbook()
    ws = wb.active
    ws.title = "Projecten"
    ws.append(["Project", "Naam", "Categorie", "Contracttype", "Status",
               "Gefactureerd", "Effectieve kost", "Marge (gefactureerd - kost)",
               "Uren gepresteerd", "Uren begroot", "Kostbron"])
    for s in sel:
        ws.append([xs(s.get("project_key")), xs(s.get("naam")), xs(s.get("categorie")),
                   xs(s.get("contracttype")), xs(s.get("summary_status")),
                   s.get("gefactureerd"), s.get("effectieve_kost"),
                   components.visible_marge(s),          # blank when nothing invoiced
                   s.get("uren_gepresteerd"), s.get("uren_begroot"),
                   xs(s.get("kost_bron"))])

    wf = wb.create_sheet("Fases")
    wf.append(["Project", "Fase", "Budget EUR", "Verbruikt EUR", "Verbruikt %",
               "Gefactureerd EUR", "Kost EUR", "Uren gepresteerd", "Uren begroot",
               "Gestart", "Inbegrepen"])
    for s in sel:
        for p in json.loads(s["phases_json"] or "[]"):
            # .get() everywhere: pre-migration phases lack billed_eur/cost_eur
            # -> blank cells, never a misleading 0.
            wf.append([xs(s.get("project_key")), xs(p.get("naam")),
                       p.get("budget_eur"), p.get("spent_eur"), p.get("pct"),
                       p.get("billed_eur"), p.get("cost_eur"),
                       p.get("tracked_hours"), p.get("budget_hours") or None,
                       "ja" if p.get("started") else "nee",
                       "ja" if p.get("applicable") else "nee"])

    bio = BytesIO()          # fresh buffer per request (never a module global)
    wb.save(bio)
    bio.seek(0)
    return send_file(
        bio, as_attachment=True,
        download_name=f"nacalculatie-analyse-{time.strftime('%Y%m%d')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------- sync ----------
@bp.post("/app/sync")
@auth.login_required
def sync_now():
    sync.trigger_sync()
    return jsonify({"ok": True})


@bp.get("/app/sync/state")
@auth.login_required
def sync_state():
    ss = store.get_sync_state()
    return jsonify({"running": bool(ss.get("running")), "last_ok_at": ss.get("last_ok_at"),
                    "projects_synced": ss.get("projects_synced")})


# ---------- beheer ----------
def _fnum(name, default=None):
    """Form field -> float, or default (never raises a 500 on bad input)."""
    try:
        return float(request.form.get(name, ""))
    except (TypeError, ValueError):
        return default


@bp.route("/app/beheer", methods=["GET", "POST"])
@auth.admin_required
def beheer():
    lang = get_lang()
    if request.method == "POST":
        form = request.form.get("form")
        if form == "rates":
            ic, ext = _fnum("internal_cost_rate"), _fnum("external_rate")
            if ic is not None and ic > 0:
                store.set_config("internal_cost_rate", ic)
            if ext is not None and ext > 0:
                store.set_config("external_rate", ext)
            sync.trigger_sync()  # recompute margins with the new rate
        elif form == "thresholds":
            store.set_config("thresholds", {
                "amber": _fnum("amber", 80), "red": _fnum("red", 100),
                "darkred": _fnum("darkred", 115)})
        elif form == "costrate":
            uid = (request.form.get("tl_user_id") or "").strip()
            eff = (request.form.get("effective_from") or "").strip()
            # _rate_for compares dates as plain strings -> only accept ISO YYYY-MM-DD.
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff):
                eff = time.strftime("%Y-%m-%d")
            rate = _fnum("eur_per_hour")
            if uid and rate is not None and rate >= 0:
                naam = next((u["name"] for u in store.get_config("tl_users", [])
                             if u.get("id") == uid), uid)
                store.add_cost_rate(uid, naam, rate, eff)
                sync.trigger_sync()  # recompute fallback costs with the new rate
        elif form == "basis":
            b = request.form.get("status_basis")
            if b in (config.DEFAULT_STATUS_BASIS, "cost", "spent"):
                store.set_config("status_basis", b)
                sync.trigger_sync()   # the % per phase is baked in at sync time
        elif form == "phases":
            tx = dict(_taxonomy())
            aliases = {}
            for line in (request.form.get("aliases") or "").splitlines():
                if "=" not in line:
                    continue
                a, b = line.split("=", 1)
                a, b = phases_mod.normalize(a), phases_mod.normalize(b)
                # Self-mapping would be a no-op; a 2-hop chain is not resolved
                # (canonical() hops once on purpose), so drop those too.
                if a and b and a != b:
                    aliases[a] = b
            tx["aliases"] = {a: b for a, b in aliases.items() if b not in aliases}
            tx["order"] = [k for k in (phases_mod.normalize(x)
                                       for x in (request.form.get("order") or "").splitlines()) if k]
            tx["overhead"] = [k for k in request.form.getlist("overhead") if k]
            store.set_config("phase_taxonomy", tx)
            sync.trigger_sync()   # overhead changes summary_status -> recompute
        elif form == "phases_optimize":
            tx = dict(_taxonomy())
            names = store.get_config("seen_phase_names", [])
            merged = dict(tx.get("aliases") or {})
            merged.update(phases_mod.suggest_aliases(names, tx))
            tx["aliases"] = merged
            tx["order"] = phases_mod.observed_order(names, tx)
            store.set_config("phase_taxonomy", tx)
            sync.trigger_sync()
        elif form == "adduser":
            if not store.get_user_by_email(request.form.get("email", "")):
                store.create_user(request.form["email"], request.form.get("naam", ""),
                                  auth.hash_password(request.form["password"]),
                                  is_admin=1 if request.form.get("is_admin") else 0)
        # Post/Redirect/Get: a browser refresh must not re-submit (would add a
        # duplicate cost-rate row -- cost_rates has no unique constraint).
        return redirect("/app/beheer?saved=1")
    saved = request.args.get("saved") == "1"
    users = store.list_users()
    thresholds = store.get_config("thresholds", config.DEFAULT_THRESHOLDS)
    internal_rate = store.get_config("internal_cost_rate", config.DEFAULT_INTERNAL_COST_RATE)
    external_rate = store.get_config("external_rate", config.DEFAULT_EXTERNAL_RATE)
    tx = _taxonomy()
    seen_names = store.get_config("seen_phase_names", [])
    # One entry per CANONICAL phase (aliases already collapsed), in quote order.
    seen = {}
    for n in seen_names:
        c = phases_mod.canonical(n, tx)
        seen.setdefault(c["key"], (c["order"], c["label"]))
    seen_keys = [(k, lbl) for k, (_o, lbl) in sorted(seen.items(), key=lambda kv: kv[1])]
    content = pages.render_beheer(lang, users, thresholds, internal_rate, external_rate, saved,
                                  has_tl_costs=store.get_config("has_project_costs", None),
                                  tl_users=store.get_config("tl_users", []),
                                  cost_rates=store.list_cost_rates(),
                                  taxonomy=tx, seen_keys=seen_keys,
                                  suggestions=phases_mod.suggest_aliases(seen_names, tx),
                                  basis=store.get_config("status_basis",
                                                         config.DEFAULT_STATUS_BASIS))
    return render_page("beheer", t("be_title", lang), "", content)
