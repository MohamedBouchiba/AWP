"""Routes/pages for the nacalculatie dashboard (blueprint 'nacalc')."""
import json
import re

from flask import (Blueprint, request, redirect, session, jsonify, make_response)

from . import store, auth, sync, config
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
    snaps = store.list_snapshots(architectuur_only=True)
    over = sum(1 for s in snaps if s["summary_status"] == "over")
    warn = sum(1 for s in snaps if s["summary_status"] == "warn")
    tot_marge = sum(s["marge"] for s in snaps if s["marge"] is not None)
    kpis = [
        {"lab": t("kpi_running", lang), "val": len(snaps), "meta": t("kpi_meta_arch", lang), "cls": ""},
        {"lab": t("kpi_over", lang), "val": over, "meta": t("kpi_meta_action", lang) if over else t("kpi_meta_ok", lang), "cls": "up" if over else "ok"},
        {"lab": t("kpi_warn", lang), "val": warn, "meta": t("kpi_meta_warn", lang), "cls": "up" if warn else ""},
        {"lab": t("kpi_margin", lang), "val": components.eur(tot_marge), "meta": t("kpi_meta_margin", lang), "cls": "ok" if tot_marge >= 0 else "up"},
    ]
    cats = sorted({s["categorie"] for s in snaps if s["categorie"]})
    cons = sorted({s["contracttype"] for s in snaps if s["contracttype"]})
    ss = store.get_sync_state()
    content = pages.render_overzicht(lang, snaps, kpis, cats, cons,
                                         syncing=bool(ss.get("running")), show_rates_banner=False)
    return render_page("overzicht", t("ov_title", lang), t("ov_sub", lang), content)


@bp.get("/app/project/<pid>")
@auth.login_required
def project_detail(pid):
    s = store.get_snapshot(pid)
    if not s:
        return "", 404
    return pages.render_drawer(get_lang(), s)


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
@bp.get("/app/analyse")
@auth.login_required
def analyse():
    lang = get_lang()
    snaps = store.list_snapshots(architectuur_only=True)

    # 1) Average budget USED per phase, grouped by base name (strip leading "N. ").
    by_phase = {}
    for s in snaps:
        for p in json.loads(s["phases_json"] or "[]"):
            if p["started"] and p["pct"] is not None:
                base = re.sub(r"^\s*\d+\.\s*", "", p["naam"] or "").strip() or (p["naam"] or "")
                by_phase.setdefault(base, []).append(p["pct"])
    # (name, avg consumed %, N instances) — most-consumed first
    fases = [(naam, round(sum(v) / len(v)), len(v))
             for naam, v in sorted(by_phase.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))]

    # 2) Average margin % per contract type (only projects with a quote).
    by_con = {}
    for s in snaps:
        if s["contracttype"] and s["marge_pct"] is not None:
            by_con.setdefault(s["contracttype"], []).append(s["marge_pct"])
    contracts = [(c, round(sum(v) / len(v)), len(v)) for c, v in sorted(by_con.items())]

    # 3) Share of projects over budget per category.
    by_cat = {}
    for s in snaps:
        if s["categorie"]:
            by_cat.setdefault(s["categorie"], []).append(s["summary_status"] == "over")
    cats = [(c, round(sum(v) / len(v) * 100), len(v), sum(v)) for c, v in sorted(by_cat.items())]

    # 4) Projects with a client budget (status vs budget).
    raming = [(s["project_key"], s["summary_status"] == "over", s["budget_klant"])
              for s in snaps if s["budget_klant"]][:12]

    content = pages.render_analyse(lang, fases, contracts, cats, raming)
    return render_page("analyse", t("nav_analyse", lang), t("an_sub", lang), content)


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
@bp.route("/app/beheer", methods=["GET", "POST"])
@auth.admin_required
def beheer():
    lang = get_lang()
    saved = False
    if request.method == "POST":
        form = request.form.get("form")
        if form == "rates":
            ic = request.form.get("internal_cost_rate")
            ext = request.form.get("external_rate")
            if ic:
                store.set_config("internal_cost_rate", float(ic))
            if ext:
                store.set_config("external_rate", float(ext))
            sync.trigger_sync()  # recompute margins with the new rate
        elif form == "thresholds":
            store.set_config("thresholds", {
                "amber": float(request.form.get("amber", 80)),
                "red": float(request.form.get("red", 100)),
                "darkred": float(request.form.get("darkred", 115))})
        elif form == "adduser":
            if not store.get_user_by_email(request.form.get("email", "")):
                store.create_user(request.form["email"], request.form.get("naam", ""),
                                  auth.hash_password(request.form["password"]),
                                  is_admin=1 if request.form.get("is_admin") else 0)
        saved = True
    users = store.list_users()
    thresholds = store.get_config("thresholds", config.DEFAULT_THRESHOLDS)
    internal_rate = store.get_config("internal_cost_rate", config.DEFAULT_INTERNAL_COST_RATE)
    external_rate = store.get_config("external_rate", config.DEFAULT_EXTERNAL_RATE)
    content = pages.render_beheer(lang, users, thresholds, internal_rate, external_rate, saved)
    return render_page("beheer", t("be_title", lang), "", content)
