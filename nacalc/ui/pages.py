"""Server-rendered dashboard pages (Dutch/English). The dashboard CSS lives in
assets/css/dashboard.css and is inlined at import time (identical output to the
previous inline <style> block) — edit that .css file to restyle the dashboard.
Data comes from nacalc/views.py; formatting helpers from nacalc/ui/components.py."""
import os
from html import escape as esc

from ..i18n import t
from .components import (eur, h1, dots, bar_color, _uren_ratio_color,
                        _status_cell, _abar, visible_marge, visible_marge_pct,
                        invoiced_total, uren_txt as _uren_txt, info_bubble)

_CSS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "css")


def _load_css(name):
    with open(os.path.join(_CSS_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


STYLE = "<style>" + _load_css("dashboard.css") + "</style>"


def shell(lang, active, title, sub, content, badge, synced_text, syncing, is_admin,
          collapsed=False, stale=False, sync_tip=""):
    collapsed_cls = " collapsed" if collapsed else ""

    def navitem(view, key, icon, extra=""):
        cls = "active" if active == view else ""
        return (f'<a class="{cls}" href="/app/{view}" title="{esc(t(key,lang))}"><span class="ic">{icon}</span>'
                f'<span class="lbl">{esc(t(key,lang))}</span>{extra}</a>')
    badge_html = f'<span class="badge" id="navBadge">{badge}</span>' if badge else ""
    beheer = navitem("beheer", "nav_beheer", "⚙") if is_admin else ""
    other = "en" if lang == "nl" else "nl"
    on_nl = "on" if lang == "nl" else ""
    on_en = "on" if lang == "en" else ""
    if syncing:
        pill = (f'<span class="pill busy" id="syncPill" title="{esc(sync_tip)}">'
                f'<span class="dot"></span> {esc(t("syncing",lang))}</span>')
    else:
        cls = " stale" if stale else ""
        pill = (f'<span class="pill{cls}" id="syncPill" title="{esc(sync_tip)}">'
                f'<span class="dot"></span> {esc(synced_text)}</span>')

    def _mob(view, key, extra=""):
        cls = "active" if active == view else ""
        return f'<a class="{cls}" href="/app/{view}">{esc(t(key,lang))}{extra}</a>'
    mob_badge = f' <span class="badge">{badge}</span>' if badge else ""
    mobnav = (f'<nav class="mobnav">{_mob("overzicht","nav_overzicht")}{_mob("meldingen","nav_meldingen",mob_badge)}'
              f'{_mob("analyse","nav_analyse")}{_mob("analyse2","nav_analyse2")}'
              f'{(_mob("beheer","nav_beheer") if is_admin else "")}</nav>')
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AWP Buro — {esc(t('app_name',lang))}</title>{STYLE}</head><body>
<div class="app{collapsed_cls}">
<button class="rail-toggle" type="button" onclick="toggleSidebar()" aria-label="{esc(t('sidebar_toggle',lang))}" title="{esc(t('sidebar_toggle',lang))}"></button>
<aside class="side">
  <a class="brand" href="/app" title="AWP Buro"><div class="logo">AWP</div><div class="bt"><b>AWP Buro</b><span>{esc(t('app_name',lang))}</span></div></a>
  <nav class="nav">
    {navitem("overzicht","nav_overzicht","▦")}
    {navitem("meldingen","nav_meldingen","◔", badge_html)}
    {navitem("analyse","nav_analyse","▥")}
    {navitem("analyse2","nav_analyse2","◫")}
    {beheer}
  </nav>
  <div class="side-foot">
    <div class="langs"><a class="{on_nl}" href="/app/lang/nl">NL</a> · <a class="{on_en}" href="/app/lang/en">EN</a></div>
    <a class="lo" href="/app/logout" title="{esc(t('logout',lang))}">{esc(t('logout',lang))}</a>
    <div class="src">Databron: Teamleader</div>
  </div>
</aside>
<div class="main">
  {mobnav}
  <div class="top">
    <div><h1>{esc(title)}</h1><div class="sub">{esc(sub)}</div></div>
    <div class="spacer"></div>
    {pill}
    <button class="btn" onclick="syncNow(this)">{esc(t('sync_now',lang))}</button>
  </div>
  <div class="content">{content}</div>
</div></div>
<div class="scrim" id="scrim" onclick="closeDrawer()"></div>
<div class="drawer" id="drawer"></div>
<script>
function openDrawer(id){{fetch('/app/project/'+id).then(r=>r.text()).then(h=>{{document.getElementById('drawer').innerHTML=h;document.getElementById('drawer').classList.add('show');document.getElementById('scrim').classList.add('show');}});}}
function closeDrawer(){{document.getElementById('drawer').classList.remove('show');document.getElementById('scrim').classList.remove('show');}}
function syncNow(b){{b.disabled=true;b.textContent='…';fetch('/app/sync',{{method:'POST'}}).then(()=>poll());}}
function poll(){{fetch('/app/sync/state').then(r=>r.json()).then(s=>{{var p=document.getElementById('syncPill');if(s.running){{p.innerHTML='<span class="dot" style="background:var(--amber)"></span> {esc(t('syncing',lang))}';setTimeout(poll,2500);}}else{{location.reload();}}}});}}
function applyFilters(){{var c=v('fCat'),ct=v('fCon'),st=v('fSt'),q=(v('fSearch')||'').toLowerCase(),g=v('fGestart');var vis=0;
document.querySelectorAll('#rows tr[data-nr]').forEach(function(tr){{var d=tr.dataset;var ok=(!c||d.cat===c)&&(!ct||d.con===ct)&&(!st||d.st===st)&&(!q||(d.search||'').indexOf(q)>=0)&&(g!=='ja'||(d.started||'0')!=='0');tr.style.display=ok?'':'none';if(ok)vis++;}});
var nr=document.getElementById('noRows');if(nr){{nr.style.display=vis?'none':'';}}}}
function v(id){{var e=document.getElementById(id);return e?e.value:'';}}
function sortTable(key,numeric){{var tb=document.getElementById('rows');if(!tb)return;var rows=[].slice.call(tb.querySelectorAll('tr'));var same=tb.getAttribute('data-sk')===key&&tb.getAttribute('data-sd')==='1';var dir=same?-1:1;rows.sort(function(a,b){{var x=a.dataset[key]||'',y=b.dataset[key]||'';if(numeric){{return ((parseFloat(x)||0)-(parseFloat(y)||0))*dir;}}return String(x).localeCompare(String(y))*dir;}});rows.forEach(function(r){{tb.appendChild(r);}});tb.setAttribute('data-sk',key);tb.setAttribute('data-sd',dir===1?'1':'0');}}
function toggleSidebar(){{var a=document.querySelector('.app');var c=a.classList.toggle('collapsed');document.cookie='sidebar='+(c?'collapsed':'open')+';path=/;max-age=31536000;samesite=Lax';}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeDrawer();}});
var SYNCING={"true" if syncing else "false"};
if(SYNCING){{poll();}}
if(document.getElementById('fGestart')){{applyFilters();}}
</script>
</body></html>"""

def login_page(lang, error):
    err = f'<div class="err">{esc(t("login_err",lang))}</div>' if error else ""
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AWP Buro — {esc(t('login_title',lang))}</title>{STYLE}</head>
<body><div class="login-wrap"><form class="login" method="post" action="/app/login">
<h1>AWP Buro</h1><p>{esc(t('app_name',lang))}</p>{err}
<label>{esc(t('login_email',lang))}</label><input name="email" type="email" autofocus required>
<label>{esc(t('login_pw',lang))}</label><input name="password" type="password" required>
<button type="submit">{esc(t('login_btn',lang))}</button>
<div style="margin-top:14px;text-align:center;font-size:12px"><a href="/app/login?lang=nl">NL</a> · <a href="/app/login?lang=en">EN</a></div>
</form></div></body></html>"""

def _ov_selectbar(lang, verantws, f):
    """Server-side selection: period + owner.

    A plain GET form, because these two must also drive the KPI cards. The
    search / categorie / contract / status controls below stay client-side —
    they only hide table rows and leave the KPIs untouched.
    """
    def opt(val, key):
        sel = " selected" if f.get("period") == val else ""
        return f'<option value="{val}"{sel}>{esc(t(key,lang))}</option>'
    per = ('<select name="period" onchange="this.form.submit()">'
           + opt("", "an_period_all") + opt("1", "an_period_1") + opt("3", "an_period_3")
           + opt("6", "an_period_6") + opt("12", "an_period_12") + '</select>')
    cur = f.get("verantw") or ""
    vopts = "".join(
        f'<option value="{esc(v)}"{" selected" if v == cur else ""}>{esc(v)}</option>'
        for v in (verantws or []))
    ver = (f'<select name="verantw" onchange="this.form.submit()">'
           f'<option value="">{esc(t("f_all_verantw",lang))}</option>{vopts}</select>')
    note = ""
    if f.get("n_sel") != f.get("n_all"):
        note = (f'<span class="pill type-pill">'
                f'{esc(t("ov_sel_note",lang).format(n=f.get("n_sel"), total=f.get("n_all")))}</span>'
                f'<a class="btn" href="/app">{esc(t("an_reset",lang))}</a>')
    return f'<form class="filters" method="get" action="/app">{per}{ver}{note}</form>'


def render_overzicht(lang, snaps, kpis, cats, cons, syncing=False, show_rates_banner=False,
                     verantws=None, fstate=None):
    import json
    selectbar = _ov_selectbar(lang, verantws, fstate or {})
    if not snaps:
        if syncing:
            return (f'<div class="state"><div class="sp"></div>'
                    f'<h3>{esc(t("first_sync",lang))}</h3><p>{esc(t("first_sync_sub",lang))}</p></div>')
        # Keep the bar: an empty result is usually the filter, and the user needs
        # a way back.
        return selectbar + f'<div class="state"><h3>{esc(t("empty_nodata",lang))}</h3></div>'
    rank = {"over": 3, "warn": 2, "ok": 1, "none": 0}
    banner = ""
    if show_rates_banner:
        banner = (f'<div class="rbanner">💡 {esc(t("rates_banner",lang))}'
                  f'<a href="/app/beheer">{esc(t("rates_banner_btn",lang))}</a></div>')
    kpi_html = "".join(
        f'<div class="kpi"><div class="lab">{esc(k["lab"])}</div><div class="val">{esc(str(k["val"]))}</div>'
        f'<div class="meta {k.get("cls","")}">{esc(k["meta"])}</div></div>' for k in kpis)
    cat_opts = "".join(f'<option>{esc(c)}</option>' for c in cats if c)
    con_opts = "".join(f'<option>{esc(c)}</option>' for c in cons if c)
    legend = (f'<div class="legend-ph"><span style="font-weight:700;color:var(--ink)">{esc(t("lg_fases",lang))}</span>'
              f'<span class="li"><span class="pdot c-good st-done"></span> {esc(t("lg_done",lang))}</span>'
              f'<span class="li"><span class="pdot c-good st-progress" style="animation:none"></span> {esc(t("lg_progress",lang))}</span>'
              f'<span class="li"><span class="pdot c-warn"></span> {esc(t("lg_warn",lang))}</span>'
              f'<span class="li"><span class="pdot c-over"></span> {esc(t("lg_over",lang))}</span>'
              f'<span class="li"><span class="pdot c-todo"></span> {esc(t("lg_todo",lang))}</span>'
              f'<span class="li"><span class="pdot c-none"></span> {esc(t("lg_na",lang))}</span></div>')
    rows = []
    for s in snaps:
        phases = json.loads(s["phases_json"] or "[]")
        n_started = sum(1 for p in phases if p.get("started"))
        # Hours vs budget over the STARTED phases only. Counting the budget of
        # phases nobody has touched yet is what made A346 read "91% of hours"
        # while two of its phases were genuinely over budget -- the exact
        # contradiction the client reported. Pre-migration rows have neither
        # column, so they keep the old project-wide totals.
        bg, gp = s.get("uren_begroot_gestart"), s.get("uren_gepresteerd_gestart")
        if bg is None or gp is None:
            bg, gp = s["uren_begroot"], s["uren_gepresteerd"]
        begroot, gepr = bg or 0, gp or 0
        r = gepr / begroot if begroot else 0
        rowcls, stcell = _status_cell(lang, s)
        marge = visible_marge(s)   # None unless something is actually invoiced
        if marge is not None:
            marge_chip = f'<span class="marge-chip {"pos" if marge >= 0 else "neg"}">{eur(marge)}</span>'
        else:
            marge_chip = f'<span style="color:var(--muted)" title="{esc(t("marge_none_tip",lang))}">—</span>'
        sub = esc(s["adres"] or s["categorie"] or "")
        search = esc(" ".join(str(x) for x in [s["project_key"], s["naam"], s["adres"],
                     s["verantw_arch"]] if x).lower())
        rows.append(
            f'<tr class="row-{rowcls}" data-cat="{esc(s["categorie"] or "")}" data-con="{esc(s["contracttype"] or "")}"'
            f' data-st="{ {"over":"over","warn":"warn","ok":"ok","none":""}[s["summary_status"]] }" data-search="{search}"'
            f' data-status="{rank.get(s["summary_status"],0)}" data-offerte="{s["offerte_awp"] or 0}"'
            f' data-marge="{marge if marge is not None else 0}" data-pct="{r*100:.0f}" data-nr="{esc(s["project_key"] or "")}"'
            f' data-started="{n_started}"'
            f' onclick="openDrawer(\'{s["project_id"]}\')">'
            f'<td>{stcell}</td>'
            f'<td><div class="pcell"><span class="pkey">{esc(s["project_key"] or "—")}</span>'
            f'<div class="pname">{esc(s["naam"] or "")}</div><div class="psub">{sub}</div></div></td>'
            f'<td class="who"><b>{esc(s["verantw_arch"] or "—")}</b><span>{esc(s["verantw_medewerker"] or "")}</span></td>'
            f'<td><span class="tag">{esc(s["categorie"] or "—")}</span></td>'
            f'<td><span class="tag">{esc(s["contracttype"] or "—")}</span></td>'
            f'<td class="num">{eur(s["budget_klant"])}</td>'
            f'<td class="num">{eur(s["offerte_awp"])}</td>'
            f'<td title="{esc(t("uren_gestart_tip",lang))}"><div class="bar"><i style="width:{min(r*100,100):.0f}%;background:{_uren_ratio_color(r)}"></i></div>'
            f'<div class="barlab">{_uren_txt(gepr, begroot)}{(f" · {r*100:.0f}%" if begroot else "")}</div></td>'
            f'<td>{dots(phases)}</td>'
            f'<td class="num">{marge_chip}</td></tr>')
    body = "".join(rows) or (f'<tr><td colspan="10" style="text-align:center;color:var(--muted);padding:30px">{esc(t("no_projects",lang))}</td></tr>')
    return f"""{banner}{selectbar}<div class="kpis">{kpi_html}</div>
<div class="filters">
<div class="search"><input id="fSearch" oninput="applyFilters()" placeholder="{esc(t('f_search',lang))}"></div>
<select id="fCat" onchange="applyFilters()"><option value="">{esc(t('f_all_cat',lang))}</option>{cat_opts}</select>
<select id="fCon" onchange="applyFilters()"><option value="">{esc(t('f_all_con',lang))}</option>{con_opts}</select>
<select id="fSt" onchange="applyFilters()"><option value="">{esc(t('f_all_st',lang))}</option>
<option value="over">{esc(t('f_over',lang))}</option><option value="warn">{esc(t('f_warn',lang))}</option><option value="ok">{esc(t('f_ok',lang))}</option></select>
<select id="fGestart" onchange="applyFilters()"><option value="">{esc(t('f_started_all',lang))}</option><option value="ja" selected>{esc(t('f_started_only',lang))}</option></select>
<span class="pill type-pill">{esc(t('type_arch',lang))}</span></div>
{legend}
<div class="card"><div class="tablewrap"><table><thead><tr>
<th class="sortable" onclick="sortTable('status',1)">{esc(t('th_status',lang))}<span class="ar">⇅</span></th>
<th class="sortable" onclick="sortTable('nr',0)">{esc(t('th_project',lang))}<span class="ar">⇅</span></th>
<th>{esc(t('th_owner',lang))}</th><th>{esc(t('th_cat',lang))}</th><th>{esc(t('th_con',lang))}</th>
<th class="num">{esc(t('th_budget_klant',lang))}</th>
<th class="num sortable" onclick="sortTable('offerte',1)">{esc(t('th_offerte',lang))}<span class="ar">⇅</span></th>
<th class="sortable" onclick="sortTable('pct',1)">{esc(t('th_uren',lang))}<span class="ar">⇅</span></th>
<th class="sortable" onclick="sortTable('started',1)">{esc(t('th_fases',lang))}<span class="ar">⇅</span></th>
<th class="num sortable" onclick="sortTable('marge',1)">{esc(t('th_marge',lang))}<span class="ar">⇅</span></th>
</tr></thead><tbody id="rows">{body}<tr id="noRows" style="display:none"><td colspan="10" style="text-align:center;color:var(--muted);padding:30px">{esc(t('no_projects',lang))}</td></tr></tbody></table></div></div>
<div class="foot-note">{esc(t('ov_foot',lang))}</div>"""

def _per_person(lang, s, is_admin, user_names):
    """'Uren per medewerker' table. Hours are visible to every logged-in user;
    the cost/rate column is ADMIN-ONLY and is therefore built server-side --
    a non-admin never receives the numbers in the HTML at all.

    Teamleader's API does not expose cost per person (only the project/group
    total), so per-person cost is filled in only when a rate exists in Beheer.
    """
    import json
    rows = json.loads(s.get("uren_per_persoon_json") or "[]")
    if not rows:
        return ""
    names = user_names or {}
    # The per-person cost comes from the Beheer rates. When the total above is
    # Teamleader's own cost, the two have different bases and would not add up,
    # so we show hours only and say why -- never two numbers that can't reconcile.
    show_cost = is_admin and s.get("kost_bron") in ("rates", "flat")
    head = (f'<th style="text-align:left">{esc(t("dr_pp_name",lang))}</th>'
            f'<th class="num">{esc(t("dr_pp_hours",lang))}</th>')
    if show_cost:
        head += f'<th class="num">{esc(t("dr_pp_cost",lang))}</th>'
    body = ""
    for r in rows:
        naam = names.get(r.get("uid")) or r.get("uid") or "—"
        body += (f'<tr><td>{esc(str(naam))}</td>'
                 f'<td class="num">{h1(r.get("hours"))}u</td>')
        if show_cost:
            c = r.get("cost")
            body += (f'<td class="num">{eur(c)}</td>' if c is not None
                     else f'<td class="num" title="{esc(t("dr_pp_none",lang))}">—</td>')
        body += "</tr>"
    if is_admin and s.get("kost_bron") == "teamleader":
        cap = t("dr_pp_tl_note", lang)
    elif show_cost and any(r.get("cost") is None for r in rows):
        cap = t("dr_pp_partial", lang)
    else:
        cap = ""
    cap_html = (f'<div style="font-size:10.5px;color:var(--muted);padding:6px 2px 2px">{esc(cap)}</div>'
                if cap else "")
    return (f'<div class="sec-t">{esc(t("dr_pp_title",lang))}</div>'
            f'<div class="card" style="padding:2px 14px 6px"><table class="pp"><thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table>{cap_html}</div>')


def render_drawer(lang, s, is_admin=False, user_names=None, afgerond=False,
                  afgerond_maanden=3, thresholds=None):
    import json
    phases = json.loads(s["phases_json"] or "[]")
    chip_map = {"over": ("c-over", t("st_over", lang)), "warn": ("c-warn", t("st_warn", lang)),
                "ok": ("c-ok", t("st_ok", lang)), "none": ("", t("st_notstarted", lang))}
    chipcls, chiptx = chip_map.get(s["summary_status"], ("", ""))
    # Say plainly which numbers decide this badge: it follows the HOURS, while
    # the per-phase bars below stay in euros.
    _th = thresholds or {"amber": 80, "red": 100}
    status_info = info_bubble(t("dr_status_title", lang), [
        ("ok", t("dr_status_r1", lang)),
        ("ok", t("dr_status_r2", lang)),
    ], t("dr_status_note", lang).format(a=_th.get("amber", 80), r=_th.get("red", 100)))
    fase_rows = []
    for p in phases:
        if not p["applicable"]:
            fase_rows.append(f'<div class="fase-row fase-na"><div class="fr-top">'
                             f'<span class="fr-name">{esc(p["naam"])}</span><span class="tag">{esc(t("ph_na",lang))}</span></div></div>')
            continue
        r = (p["pct"] or 0) / 100
        if not p["started"]:
            lab = t("ph_none", lang)
        elif p["done"]:
            lab = t("ph_done", lang)
        elif p["color"] == "darkred":
            lab = t("ph_crit", lang)
        elif p["color"] == "red":
            lab = t("ph_over", lang)
        elif p["color"] == "amber":
            lab = t("ph_warn", lang)
        else:
            lab = t("ph_progress", lang)
        fase_rows.append(
            f'<div class="fase-row"><div class="fr-top"><span class="fr-name">{esc(p["naam"])}</span>'
            f'<span class="tag" style="color:{bar_color(p["color"])}">{esc(lab)}</span></div>'
            f'<div class="fbar"><i style="width:{min(r*100,100):.0f}%;background:{bar_color(p["color"])}"></i></div>'
            f'<div class="fr-meta"><span>{eur(p.get("verbruikt_eur", p["spent_eur"]))} / {eur(p["budget_eur"])} {esc(t("ph_verbruikt",lang))}</span><span>{p["pct"] if p["pct"] is not None else 0}%</span></div>'
            f'<div class="fr-meta"><span>{_uren_txt(p.get("tracked_hours"), p.get("budget_hours"))} {esc(t("ph_uren_lab",lang))}</span></div></div>')
    # Say which two numbers the per-phase % actually compares -- the client's
    # confusion on A346 was exactly about this.
    basis_note = t("ph_basis_spent" if (phases and phases[0].get("basis") == "spent")
                   else "ph_basis_cost", lang)
    # Teamleader has no time budget on (some) phases -> explain the dashes.
    budget_missing = any(p.get("applicable") and not p.get("budget_hours") for p in phases)
    note = (f'<div style="font-size:11px;color:var(--muted);margin-top:6px">{esc(t("ph_budget_missing",lang))}</div>'
            if budget_missing else "")
    kost_html = eur(s["effectieve_kost"]) if s["effectieve_kost"] is not None else f'<span style="font-size:12px;color:var(--muted)">{esc(t("rates_missing",lang))}</span>'
    src_key = {"teamleader": "kost_src_tl", "rates": "kost_src_rates",
               "flat": "kost_src_flat"}.get(s.get("kost_bron"))
    est = (f'<div style="font-size:10.5px;color:var(--muted);font-weight:600;margin-top:2px">{esc(t(src_key,lang))}</div>'
           if src_key else
           (f' <span style="font-size:11px;color:var(--muted)">{esc(t("estimate_flag",lang))}</span>'
            if s["cost_estimated"] else ""))
    mv, mp = visible_marge(s), visible_marge_pct(s)
    marge_html = (f'{eur(mv)} · {mp}%' if mv is not None
                  else f'<span title="{esc(t("marge_none_tip",lang))}">—</span>')
    marge_col = "var(--green)" if (mv or 0) >= 0 else "var(--red)"
    pp_html = _per_person(lang, s, is_admin, user_names)

    # Hours over the STARTED phases (see render_overzicht), with the full budget
    # kept visible underneath so nothing looks hidden.
    bg, gp = s.get("uren_begroot_gestart"), s.get("uren_gepresteerd_gestart")
    if bg is None or gp is None:
        bg, gp = s["uren_begroot"], s["uren_gepresteerd"]
    # Which phases feed that hours figure, and which don't. A bare "129.3 / —"
    # said nothing; the count and the reasons belong in a tooltip, not in the
    # value line.
    _inc = [p for p in phases if p.get("started") and p.get("applicable")]
    _exc = [(p, t("ph_reason_nobudget" if not p.get("applicable") else "ph_reason_notstarted", lang))
            for p in phases if not (p.get("started") and p.get("applicable"))]
    # Two lines, no more: the count of what is in, and the count of what is out
    # with those named in brackets. Listing the included phases as well just
    # buried the answer.
    _rows = [("ok", t("dr_uren_tip_head", lang).format(n=len(_inc)))]
    if _exc:
        # Cap the list: on a project where nothing has started yet this named
        # all ten phases, which is the wall of text the bubble exists to avoid.
        _names = [p["naam"] for p, _r in _exc]
        _shown = ", ".join(_names[:3])
        if len(_names) > 3:
            _shown += t("dr_uren_tip_more", lang).format(n=len(_names) - 3)
        _rows.append(("no", t("dr_uren_tip_out", lang).format(m=len(_exc), lijst=_shown)))
    # Overhead is counted HERE but deliberately ignored by the budget status,
    # and that is exactly the distinction people trip over.
    _note = " ".join(
        [t("dr_uren_tip_overhead", lang).format(naam=p["naam"]) for p in _inc if p.get("overhead")]
        + ([t("dr_uren_tip_total", lang).format(n=h1(s["uren_begroot"]))]
           if s.get("uren_begroot") else []))
    uren_info = info_bubble(t("dr_uren_tip_title", lang), _rows, _note)
    uren_sub = (f'<div class="mc-sub">{esc(t("dr_uren_sub",lang).format(n=h1(bg)))}</div>'
                if bg else f'<div class="mc-sub">{esc(t("dr_uren_sub_none",lang))}</div>')
    # Invoices sent outside Teamleader: admin-only, and it posts as a normal form
    # (the drawer is injected HTML, so any <script> in here would never run).
    gef_extra = ""
    if is_admin:
        cur = s.get("gefactureerd_manueel")
        gef_extra = (
            f'<form class="mc-inline" method="post" action="/app/project/{esc(s["project_id"])}/gefactureerd">'
            f'<label>{esc(t("dr_gef_manueel",lang))}</label>'
            f'<input name="bedrag" type="number" step="0.01" placeholder="0.00"'
            f' value="{"" if cur is None else cur}">'
            f'<button class="btn" type="submit">{esc(t("dr_gef_save",lang))}</button></form>')
    elif s.get("gefactureerd_manueel"):
        gef_extra = (f'<div class="mc-sub">{esc(t("dr_gef_manueel",lang))} '
                     f'{eur(s.get("gefactureerd_manueel"))}</div>')

    # Finished / running. Automatic by inactivity, overridable per project --
    # Teamleader keeps every AWP project "open", so there is nothing to read.
    af_lab = t("dr_afgerond_ja" if afgerond else "dr_afgerond_nee", lang)
    if is_admin:
        cur = s.get("afgerond_manueel")
        def _o(val, key):
            v = "" if val is None else str(val)
            return (f'<option value="{v}"'
                    f'{" selected" if (cur if cur is None else int(cur)) == val else ""}>'
                    f'{esc(t(key,lang))}</option>')
        af_html = (
            f'<form class="mc-inline" method="post" action="/app/project/{esc(s["project_id"])}/afgerond">'
            f'<select name="afgerond" onchange="this.form.submit()">'
            f'{_o(None, "dr_afgerond_auto")}{_o(1, "dr_afgerond_ja")}{_o(0, "dr_afgerond_nee")}'
            f'</select></form>')
    else:
        af_html = ""
    # The rule was three lines of blue text in the cell; it belongs in a bubble.
    af_info = info_bubble(t("dr_afgerond_title", lang), [
        ("", t("dr_afgerond_rule", lang).format(n=afgerond_maanden)),
        ("", t("dr_afgerond_why", lang)),
    ])
    return f"""<div class="dr-head"><button class="x" onclick="closeDrawer()">×</button>
<h2>{esc(s["project_key"] or "")} · {esc(s["naam"] or "")}</h2>
<div class="m">{esc(s["adres"] or "")} &nbsp;•&nbsp; {esc(s["verantw_arch"] or "")}</div>
<div style="margin-top:10px;display:flex;gap:8px;align-items:center"><span class="tag">{esc(s["categorie"] or "—")}</span>
<span class="tag">{esc(s["contracttype"] or "—")}</span><span class="status-chip {chipcls}" style="font-weight:700;font-size:12px;padding:4px 10px;border-radius:20px">● {esc(chiptx)}</span>{status_info}</div></div>
<div class="dr-body"><div class="meta-grid">
<div class="mc"><div class="l">{esc(t('dr_budget_klant',lang))}</div><div class="v">{eur(s["budget_klant"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_raming',lang))}</div><div class="v">{eur(s["raming_vo"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_offerte',lang))}</div><div class="v">{eur(s["offerte_awp"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_gefactureerd',lang))}</div><div class="v">{eur(invoiced_total(s) or None)}</div>{gef_extra}</div>
<div class="mc"><div class="l">{esc(t('dr_uren_gestart',lang))}{uren_info}</div><div class="v">{h1(gp)}u</div>{uren_sub}</div>
<div class="mc"><div class="l">{esc(t('dr_werfbezoek',lang))}</div><div class="v">{s["werfbezoeken"] or 0}</div></div>
<div class="mc"><div class="l">{esc(t('dr_bespreking',lang))}</div><div class="v">{s["besprekingen"] or 0}</div></div>
<div class="mc"><div class="l">{esc(t('dr_afgerond',lang))}{af_info}</div><div class="v">{esc(af_lab)}</div>{af_html}</div>
<div class="mc"><div class="l">{esc(t('dr_kost',lang))}</div><div class="v">{kost_html}{est}</div></div>
<div class="mc"><div class="l">{esc(t('dr_marge',lang))}</div><div class="v" style="color:{marge_col}">{marge_html}</div></div>
</div>
<div class="sec-t">{esc(t('dr_voortgang',lang))}</div>{"".join(fase_rows)}
<div style="font-size:11px;color:var(--muted);margin-top:4px;line-height:1.4">{esc(basis_note)} {esc(t('ph_caption',lang))}</div>{note}
{pp_html}</div>"""

def melding_text(lang, m):
    """The message for one alert, rendered at DISPLAY time.

    Not stored: a message written into the row would stay frozen in whichever
    language the sync happened to run in.
    """
    if m.get("soort") == "project":
        return t("ml_m_project", lang).format(pct=m.get("pct"))
    key = {"amber": "ml_m_amber", "red": "ml_m_red"}.get(m["severity"], "ml_m_darkred")
    return t(key, lang).format(f=m.get("phase_naam") or "", pct=m.get("pct"))


def render_meldingen(lang, items, scope="mijn", show_done=False, is_admin=False,
                     unlinked=False):
    """The alert list: mine by default, everything for an admin who asks.

    One row per threshold crossed — a phase at 120% shows three, exactly as the
    client specified ("maximaal drie meldingen, elk exact één keer"). Handled
    alerts drop out of the list and do not come back.
    """
    def link(sc, done, label, on):
        q = f"?scope={sc}" + ("&done=1" if done else "")
        return (f'<a class="ml-tab{" on" if on else ""}" href="/app/meldingen{q}">'
                f'{esc(label)}</a>')
    tabs = [link("mijn", show_done, t("ml_scope_mine", lang), scope == "mijn")]
    if is_admin or unlinked:
        tabs.append(link("alle", show_done, t("ml_scope_all", lang), scope == "alle"))
    tabs.append(link(scope, not show_done,
                     t("ml_hide_done" if show_done else "ml_show_done", lang), False))
    head = (f'<p class="panel-s" style="margin-bottom:12px">{esc(t("ml_sub",lang))}</p>'
            f'<div class="ml-tabs">{"".join(tabs)}</div>')
    if unlinked:
        head += f'<div class="rbanner">💡 {esc(t("ml_unlinked",lang))}<a href="/app/beheer">Beheer</a></div>'
    if not items:
        return (head + f'<div class="card" style="padding:30px;text-align:center;color:var(--muted)">'
                f'{esc(t("ml_none_open",lang))}</div>')

    out = [head]
    for m in items:
        project = m.get("soort") == "project"
        over = m["severity"] in ("red", "darkred") or m["severity"] == "p100"
        col = "var(--red)" if over else "var(--amber)"
        icon = "📊" if project else ("🔴" if over else "🟠")
        done = m.get("afgehandeld_at")
        if done:
            act = (f'<form method="post" action="/app/meldingen/{m["id"]}/heropenen" class="ml-act">'
                   f'<button class="btn" type="submit">↩ {esc(t("ml_reopen",lang))}</button></form>')
        else:
            act = (f'<form method="post" action="/app/meldingen/{m["id"]}/afhandelen" class="ml-act">'
                   f'<button class="btn ml-ok" type="submit" title="{esc(t("ml_do_tip",lang))}">'
                   f'✓ {esc(t("ml_do",lang))}</button></form>')
        soort = t("ml_p_soort" if project else "ml_f_soort", lang)
        who = (f'<span class="ml-who">{esc(m["verantw"])}</span>'
               if m.get("verantw") else "")
        out.append(
            f'<div class="alert{" is-project" if project else ""}{" is-done" if done else ""}">'
            f'<div class="ai {"ai-over" if over else "ai-warn"}">{icon}</div>'
            # Everything the client asked an alert to carry: project number and
            # name, phase, percentage and owner.
            f'<div><div class="at">{esc(m["project_key"] or "")} · {esc(m["naam"] or "")}'
            f'<span class="ml-kind">{esc(soort)}</span>'
            f'{who}</div>'
            f'<div class="ad">{esc(melding_text(lang, m))}</div></div>'
            f'<div class="ax"><div class="pct" style="color:{col}">{m["pct"]}%</div>{act}'
            f'<button class="btn" onclick="openDrawer(\'{m["project_id"]}\')">{esc(t("ml_view",lang))} →</button></div></div>')
    return "".join(out)

def _analyse_filterbar(lang, f, action):
    """The shared analysis filter bar, aimed at `action` (and `action`/export).

    Period / custom range / project selection are mutually exclusive: the JS in
    _analyse_filterjs clears the others, and _select_snapshots enforces the same
    precedence server-side. The dossier (lopend/afgerond) filter is orthogonal —
    it narrows whatever was picked.
    """
    def opt(val, key):
        sel = " selected" if f["period"] == val else ""
        return f'<option value="{val}"{sel}>{esc(t(key,lang))}</option>'
    period_sel = ('<select id="fPeriod" name="period" onchange="anPeriod()">'
                  + opt("", "an_period_all") + opt("1", "an_period_1")
                  + opt("3", "an_period_3") + opt("6", "an_period_6") + opt("12", "an_period_12")
                  + opt("custom", "an_period_custom") + '</select>')

    def dopt(val, key):
        sel = " selected" if f.get("dossier", "") == val else ""
        return f'<option value="{val}"{sel}>{esc(t(key,lang))}</option>'
    dossier_sel = ('<select name="dossier" onchange="this.form.submit()">'
                   + dopt("", "an_dossier_all") + dopt("lopend", "an_dossier_lopend")
                   + dopt("afgerond", "an_dossier_afgerond") + '</select>')
    # Self-contained searchable multi-select (no library). Search only HIDES
    # options, never removes them, so a checked-but-filtered project still submits.
    opts = "".join(
        f'<label class="ms-opt" data-lbl="{esc(lbl.lower())}">'
        f'<input type="checkbox" name="pids" value="{esc(pid)}"'
        f'{" checked" if pid in f["pids"] else ""} onchange="anPids()"> {esc(lbl)}</label>'
        for pid, lbl in f["projects"])
    ms = (f'<div class="ms" id="ms">'
          f'<button class="ms-btn" type="button" onclick="msToggle(event)" title="{esc(t("an_projects_hint",lang))}">'
          f'<span id="msLabel">{esc(t("an_ms_none",lang))}</span> ▾</button>'
          f'<div class="ms-panel" id="msPanel" hidden>'
          f'<input class="ms-search" type="text" oninput="msFilter(this.value)" placeholder="{esc(t("an_ms_placeholder",lang))}">'
          f'<div class="ms-list">{opts}</div></div></div>')
    return (f'<form class="filters" id="anForm" method="get" action="{action}">{period_sel}{dossier_sel}'
            f'<input type="month" id="fFrom" name="from" value="{esc(f["from"])}" title="{esc(t("an_from",lang))}" onchange="anRange()">'
            f'<input type="month" id="fTo" name="to" value="{esc(f["to"])}" title="{esc(t("an_to",lang))}" onchange="anRange()">'
            f'{ms}'
            f'<button class="btn" type="submit" style="height:40px">{esc(t("an_apply",lang))}</button>'
            f'<a class="btn" href="{action}" style="height:40px;display:inline-flex;align-items:center">{esc(t("an_reset",lang))}</a>'
            f'<span class="pill type-pill">{esc(t("an_sel_note",lang).format(n=f["n_sel"]))}</span>'
            f'<button class="btn btn-exp" type="submit" formaction="{action}/export">⤓ {esc(t("an_export",lang))}</button>'
            f'</form>')


def _analyse_filterjs(lang):
    ms_count_tpl = t("an_ms_count", lang).replace("{n}", "__N__")
    return f"""<script>
function msToggle(e){{var p=document.getElementById('msPanel');p.hidden=!p.hidden;if(e)e.stopPropagation();}}
function msFilter(q){{q=(q||'').toLowerCase();
document.querySelectorAll('#msPanel .ms-opt').forEach(function(o){{o.style.display=(!q||(o.dataset.lbl||'').indexOf(q)>=0)?'':'none';}});}}
function msChecked(){{return [].slice.call(document.querySelectorAll('#msPanel input[name=pids]:checked'));}}
function msSync(){{var n=msChecked().length;
document.getElementById('msLabel').textContent = n ? {ms_count_tpl!r}.replace('__N__',n) : {t("an_ms_none", lang)!r};
document.getElementById('ms').classList.toggle('has-sel', n>0);}}
function anPids(){{ // a project selection clears the period filters
  if(msChecked().length){{document.getElementById('fPeriod').value='';
    document.getElementById('fFrom').value='';document.getElementById('fTo').value='';}}
  msSync();}}
function anPeriod(){{ // choosing a period clears the range (unless custom) + projects
  var v=document.getElementById('fPeriod').value;
  if(v!=='custom'){{document.getElementById('fFrom').value='';document.getElementById('fTo').value='';}}
  msChecked().forEach(function(c){{c.checked=false;}}); msSync();}}
function anRange(){{ // typing a from/to means "custom", and clears the projects
  document.getElementById('fPeriod').value='custom';
  msChecked().forEach(function(c){{c.checked=false;}}); msSync();}}
document.addEventListener('click',function(e){{var m=document.getElementById('ms');
if(m&&!m.contains(e.target)){{document.getElementById('msPanel').hidden=true;}}}});
msSync();
</script>"""


def _an_panel(lang, tk, sk, ik, inner, empty_key="an_empty"):
    empty = f'<p class="panel-s">{esc(t(empty_key,lang))}</p>'
    return (f'<div class="card" style="padding:20px 22px"><p class="panel-t">{esc(t(tk,lang))}'
            f'<span class="pinfo" title="{esc(t(ik,lang))}">i</span></p>'
            f'<p class="panel-s">{esc(t(sk,lang))}</p>{inner or empty}</div>')


def render_analyse2(lang, q1, q2, q3, q4, q5, f):
    """Analyse 2 — geofferteerd vs kostprijs bureau, zonder facturatie.

    The client: "Alles waarbij we een gefactureerde vergelijken met iets anders
    is op vandaag nog niet super relevant, want niet alles liep hiermee. Het kan
    dat we tussentijds eerder moeten werken met een analyse 2 die geofferteerde
    vs budget/effectieve kost uitwerkt. Deze kan dan later wegvallen."

    So this page is a deliberate parallel to /app/analyse, reusing its filter
    bar, aggregation and export machinery — only the projections differ. When
    Teamleader invoicing is complete it can be dropped by deleting one route and
    one nav entry.

    q1 (label, cost, budget, pct, n) · q2 (label, tracked, budget_h, pct, n)
    q3 (label, marge, budget, cost, n) · q4/q5 (label, marge, offerte, cost, n)
    """
    bars = ""
    for naam, cost, budget, pct, n in q1:
        color = "var(--red)" if pct > 100 else "var(--amber)" if pct >= 80 else "var(--green)"
        tip = t("q1_tip", lang).format(cost=eur(cost), budget=eur(budget), pct=pct, n=n)
        bars += _abar(naam, min(pct, 100), f"{pct}%", color, tip)
    p1 = _an_panel(lang, "q1_t", "q1_s", "q1_info", bars)

    bars = ""
    for naam, tracked, budget, pct, n in q2:
        color = "var(--red)" if pct >= 100 else "var(--amber)" if pct >= 80 else "var(--green)"
        tip = t("an2_tip", lang).format(tracked=tracked, budget=budget, pct=pct, n=n)
        bars += _abar(naam, min(pct, 100), f"{pct}%", color, tip)
    p2 = _an_panel(lang, "an2_t", "an2_s", "an2_info", bars, empty_key="an2_empty")

    def profit_bars(rows, tipkey):
        mx = max((abs(m) for _, m, _b, _c, _n in rows), default=0) or 1
        out = ""
        for naam, marge, basis, cost, n in rows:
            color = "var(--green)" if marge >= 0 else "var(--red)"
            tip = t(tipkey, lang).format(basis=eur(basis), cost=eur(cost), marge=eur(marge), n=n)
            out += _abar(naam, abs(marge) / mx * 100, eur(marge), color, tip)
        return out
    p3 = _an_panel(lang, "q3_t", "q3_s", "q3_info", profit_bars(q3, "q3_tip"))
    p4 = _an_panel(lang, "q4_t", "q4_s", "q4_info", profit_bars(q4, "q4_tip"))
    p5 = _an_panel(lang, "q5_t", "q5_s", "q5_info", profit_bars(q5, "q5_tip"))

    return (f'<p class="panel-s" style="margin-bottom:12px">{esc(t("q_sub",lang))}</p>'
            f'{_analyse_filterbar(lang, f, "/app/analyse2")}'
            f'<div class="grid2">{p1}{p2}{p3}{p4}{p5}</div>{_analyse_filterjs(lang)}')


def render_analyse(lang, g1, g2, g3, g4, g5, g6, f):
    """Six graphs over the selected projects (period or explicit selection).
    g1 (naam, billed, budget, delta_pct, n) · g2 (naam, tracked, budget_h, pct, n)
    g3/g4/g6 (naam, marge, billed, cost, n) · g5 (naam, avg_h, n) · f = filter state."""
    def panel(tk, sk, ik, inner, empty_key="an_empty"):
        empty = f'<p class="panel-s">{esc(t(empty_key,lang))}</p>'
        return (f'<div class="card" style="padding:20px 22px"><p class="panel-t">{esc(t(tk,lang))}'
                f'<span class="pinfo" title="{esc(t(ik,lang))}">i</span></p>'
                f'<p class="panel-s">{esc(t(sk,lang))}</p>{inner or empty}</div>')

    fbar = _analyse_filterbar(lang, f, "/app/analyse")
    fjs = _analyse_filterjs(lang)

    # 1) Invoiced vs quote budget per phase: bar = billed/budget, label = ±delta%.
    h = ""
    for naam, billed, budget, delta, n in g1:
        color = "var(--red)" if delta > 15 else "var(--amber)" if delta > 0 else "var(--green)"
        tip = t("an1_tip", lang).format(billed=eur(billed), budget=eur(budget), delta=delta, n=n)
        h += _abar(naam, (billed / budget * 100) if budget else 0, f"{delta:+d}%", color, tip)
    p1 = panel("an1_t", "an1_s", "an1_info", h)

    # 2) Tracked vs budgeted hours per phase. Empty when Teamleader has no time
    # budget on any phase -> say so explicitly instead of "not enough data".
    h = ""
    for naam, tracked, budget, pct, n in g2:
        color = "var(--red)" if pct >= 100 else "var(--amber)" if pct >= 80 else "var(--green)"
        tip = t("an2_tip", lang).format(tracked=tracked, budget=budget, pct=pct, n=n)
        h += _abar(naam, min(pct, 100), f"{pct}%", color, tip)
    p2 = panel("an2_t", "an2_s", "an2_info", h, empty_key="an2_empty")

    # 3/4/6) Profitability (€): bar scaled to the largest |margin| in the graph.
    def profit_bars(rows, tipkey):
        mx = max((abs(m) for _, m, _b, _c, _n in rows), default=0) or 1
        out = ""
        for naam, marge, billed, cost, n in rows:
            color = "var(--green)" if marge >= 0 else "var(--red)"
            tip = t(tipkey, lang).format(billed=eur(billed), cost=eur(cost), marge=eur(marge), n=n)
            out += _abar(naam, abs(marge) / mx * 100, eur(marge), color, tip)
        return out
    p3 = panel("an3_t", "an3_s", "an3_info", profit_bars(g3, "an3_tip"))
    p4 = panel("an4_t", "an4_s", "an4_info", profit_bars(g4, "an4_tip"))
    p6 = panel("an6_t", "an6_s", "an6_info", profit_bars(g6, "an6_tip"))

    # 5) Average tracked hours per started phase.
    h = ""
    mx = max((v for _, v, _n in g5), default=0) or 1
    for naam, avg, n in g5:
        tip = t("an5_tip", lang).format(avg=avg, naam=naam, n=n)
        h += _abar(naam, avg / mx * 100, f"{avg}u", "var(--accent)", tip)
    p5 = panel("an5_t", "an5_s", "an5_info", h)

    return (f'<p class="panel-s" style="margin-bottom:12px">{esc(t("an_sub",lang))}</p>{fbar}'
            f'<div class="grid2">{p1}{p2}{p3}{p4}{p5}{p6}</div>{fjs}')

def _phase_card(lang, taxonomy, seen_keys, suggestions):
    """Beheer card for the phase taxonomy: overhead, merges, order.

    `seen_keys` is [(canonical_key, label)] observed in the last sync, so the
    admin ticks real phases instead of typing them. Aliases and order are plain
    textareas -- robust, copy-pasteable, and they survive a phase we've never
    seen (the checkbox list can't show those).
    """
    tx = taxonomy or {}
    seen_keys = seen_keys or []
    if seen_keys:
        # One row per phase, with what the setting is worth: how many projects
        # contain it, and in how many it currently sits at/over the threshold —
        # i.e. how many would actually change if you exclude it.
        # Plain checkboxes in a dense multi-column grid: 30+ phases fit in a
        # handful of rows instead of a full-height table. Ticked = counts
        # towards the budget status.
        items = []
        for d in seen_keys:
            meta = str(d["n"])
            if d["n_over"]:
                meta += f' · <b>{d["n_over"]}</b>{esc(t("be_ph_over_short", lang))}'
            items.append(
                f'<label class="ph-i{" is-oh" if d["overhead"] else ""}" '
                f'title="{esc(t("be_ph_count_tip", lang))}">'
                f'<input type="checkbox" name="meetellen" value="{esc(d["key"])}"'
                f'{"" if d["overhead"] else " checked"}>'
                f'<span class="ph-t">{esc(d["label"])}</span>'
                f'<span class="ph-m">{meta}</span></label>')
        table = (f'<div class="ph-grid">{"".join(items)}</div>'
                 # Which keys this form showed, so unticking one can be told
                 # apart from a phase the form never listed.
                 f'<input type="hidden" name="shown" value="{esc(",".join(d["key"] for d in seen_keys))}">')
    else:
        table = f'<p class="panel-s">{esc(t("be_ph_none_seen",lang))}</p>'
    alias_txt = "\n".join(f"{a} = {b}" for a, b in sorted((tx.get("aliases") or {}).items()))
    order_txt = "\n".join(tx.get("order") or [])
    sug = ""
    if suggestions:
        rows = "".join(f"<li>{esc(a)} &rarr; {esc(b)}</li>" for a, b in sorted(suggestions.items()))
        sug = (f'<p class="panel-s" style="margin-top:10px">{esc(t("be_ph_suggestions",lang))}</p>'
               f'<ul class="be-ph-sug">{rows}</ul>')
    return f"""<div class="be-card"><h2>{esc(t('be_ph_title',lang))}</h2>
<p class="panel-s">{esc(t('be_ph_sub',lang))}</p>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="phases">
<div class="be-ph-lab">{esc(t('be_ph_overhead',lang))}</div>
<div class="be-ph-hint">{esc(t('be_ph_overhead_hint',lang))}</div>
{table}
<details class="be-adv"><summary>{esc(t('be_ph_advanced',lang))}</summary>
<div class="be-ph-lab">{esc(t('be_ph_aliases',lang))}</div>
<div class="be-ph-hint">{esc(t('be_ph_aliases_hint',lang))}</div>
<textarea name="aliases" rows="4" class="be-ph-ta">{esc(alias_txt)}</textarea>
<div class="be-ph-lab">{esc(t('be_ph_order',lang))}</div>
<textarea name="order" rows="6" class="be-ph-ta">{esc(order_txt)}</textarea>
</details>
<button class="btn" style="margin-top:14px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button>
</form>
<form method="post" action="/app/beheer" style="margin-top:10px"><input type="hidden" name="form" value="phases_optimize">
<button class="btn" type="submit">✨ {esc(t('be_ph_optimize',lang))}</button>
<span class="be-ph-hint" style="margin-left:8px">{esc(t('be_ph_optimize_hint',lang))}</span></form>
{sug}</div>"""


def _basis_card(lang, basis):
    """Which two numbers the per-phase percentage compares. Reversible from the
    UI on purpose: switching back needs no redeploy, just a re-sync."""
    def radio(val, key):
        return (f'<label class="be-ph-opt"><input type="radio" name="status_basis"'
                f' value="{val}"{" checked" if basis == val else ""}> {esc(t(key,lang))}</label>')
    return f"""<div class="be-card"><h2>{esc(t('be_basis_title',lang))}</h2>
<p class="panel-s">{esc(t('be_basis_hint',lang))}</p>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="basis">
<div class="be-ph-list" style="margin-top:8px">{radio("cost", "be_basis_cost")}{radio("spent", "be_basis_spent")}</div>
<button class="btn" style="margin-top:12px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button>
</form></div>"""


def _mail_card(lang, mail_status, verantw_emails, verantws):
    configured, dry, frm = mail_status
    if not configured:
        state = f'<p class="panel-s" style="color:var(--red)">{esc(t("be_mail_off",lang))}</p>'
    elif dry:
        state = f'<p class="panel-s" style="color:var(--amber)">{esc(t("be_mail_dry",lang))}</p>'
    else:
        state = f'<p class="panel-s" style="color:var(--green)">{esc(t("be_mail_live",lang).format(**{"from": frm}))}</p>'
    # Pre-fill every owner Teamleader actually uses, so nobody is silently
    # missed just because their line was never typed.
    known = {k.strip(): v for k, v in (verantw_emails or {}).items()}
    for v in (verantws or []):
        known.setdefault(v, "")
    txt = "\n".join(f"{k} = {v}" for k, v in sorted(known.items()) if k)
    return f"""<div class="be-card"><h2>{esc(t('be_mail_title',lang))}</h2>
<p class="panel-s">{esc(t('be_mail_hint',lang))}</p>{state}
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="mail">
<div class="be-ph-lab">{esc(t('be_mail_map',lang))}</div>
<div class="be-ph-hint">{esc(t('be_mail_map_hint',lang))}</div>
<textarea name="emails" rows="6" class="be-ph-ta">{esc(txt)}</textarea>
<button class="btn" style="margin-top:12px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button>
</form></div>"""


def render_beheer(lang, users, thresholds, internal_rate, external_rate, saved,
                  has_tl_costs=None, tl_users=None, cost_rates=None,
                  taxonomy=None, seen_keys=None, suggestions=None, basis="cost",
                  mail_status=(False, True, ""), verantw_emails=None, verantws=None,
                  project_thresholds=None):
    msg = f'<div class="savemsg">{esc(t("be_saved",lang))}</div>' if saved else ""
    user_rows = "".join(
        f'<div class="be-row"><span class="nm">{esc(u["naam"] or u["email"])}</span>'
        f'<span style="color:var(--muted);font-size:12px">{esc(u["email"])}</span>'
        f'{"<span class=tag>"+esc(t("be_admin",lang))+"</span>" if u["is_admin"] else ""}</div>' for u in users)
    th = thresholds

    # Per-person cost rates (with history). Primary mode (costs from Teamleader)
    # shows them as fallback-only; fallback mode asks to fill them in.
    note_key = "be_costs_tl_note" if has_tl_costs else "be_costs_manual_note"
    tl_users = tl_users or []
    if tl_users:
        user_opts = "".join(f'<option value="{esc(u["id"])}">{esc(u["name"])}</option>' for u in tl_users)
        user_input = f'<select name="tl_user_id" required><option value="">—</option>{user_opts}</select>'
    else:
        user_input = f'<input name="tl_user_id" placeholder="Teamleader user id" required>'
    rate_rows = "".join(
        f'<div class="be-row"><span class="nm">{esc(r["tl_user_naam"] or r["tl_user_id"])}</span>'
        f'<span class="num">€{r["eur_per_hour"]:.2f}/u</span>'
        f'<span style="color:var(--muted);font-size:12px">{esc(t("be_eff_from",lang))} {esc(r["effective_from"])}</span></div>'
        for r in (cost_rates or []))
    person_rates = f"""<div class="be-card"><h2>{esc(t('be_rates',lang))}</h2>
<p class="panel-s">{esc(t(note_key,lang))}</p>
{rate_rows}
<form method="post" action="/app/beheer" style="margin-top:10px"><input type="hidden" name="form" value="costrate">
<div class="be-row">{user_input}
<input name="eur_per_hour" type="number" step="0.01" min="0" placeholder="€/u" style="width:100px" required>
<span style="font-size:12px;color:var(--muted)">{esc(t('be_eff_from',lang))}</span><input name="effective_from" type="date">
<button class="btn" type="submit">{esc(t('be_add_rate',lang))}</button></div></form></div>"""

    return f"""{msg}
<div class="be-card"><h2>{esc(t('be_rates_title',lang))}</h2>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="rates">
<div class="be-row"><span class="nm">{esc(t('be_internal_cost',lang))}</span><input name="internal_cost_rate" type="number" step="0.01" value="{internal_rate}" style="width:120px"> €/u</div>
<div class="be-row"><span class="nm">{esc(t('be_external_rate',lang))}</span><input name="external_rate" type="number" step="0.01" value="{external_rate}" style="width:120px"> €/u</div>
<button class="btn" style="margin-top:14px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button></form></div>
{person_rates}
<div class="be-card"><h2>{esc(t('be_thresholds',lang))}</h2>
<p class="panel-s">{esc(t('be_thresholds_hint',lang))}</p>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="thresholds">
<div class="be-row">amber ≥ <input name="amber" type="number" value="{th['amber']}" style="width:80px"> %
&nbsp; red &gt; <input name="red" type="number" value="{th['red']}" style="width:80px"> %
&nbsp; dark-red ≥ <input name="darkred" type="number" value="{th['darkred']}" style="width:80px"> %</div>
<button class="btn" style="margin-top:8px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button></form></div>
<div class="be-card"><h2>{esc(t('be_pth_title',lang))}</h2>
<p class="panel-s">{esc(t('be_pth_hint',lang))}</p>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="project_thresholds">
<div class="be-row">{"".join(f'<input name="p{i+1}" type="number" min="1" max="999" value="{v}" style="width:90px"> %&nbsp;&nbsp;' for i, v in enumerate((project_thresholds or [80, 90, 100])[:3]))}</div>
<button class="btn" style="margin-top:8px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button></form></div>
{_basis_card(lang, basis)}
{_phase_card(lang, taxonomy, seen_keys, suggestions)}
{_mail_card(lang, mail_status, verantw_emails, verantws)}
<div class="be-card"><h2>{esc(t('be_users',lang))}</h2>{user_rows}
<form method="post" action="/app/beheer" style="margin-top:14px"><input type="hidden" name="form" value="adduser">
<div class="be-row"><input name="naam" placeholder="Naam" required><input name="email" type="email" placeholder="E-mail" required>
<input name="password" type="password" placeholder="Wachtwoord" required>
<label style="font-size:12px"><input type="checkbox" name="is_admin"> {esc(t('be_admin',lang))}</label>
<button class="btn" type="submit">{esc(t('be_add_user',lang))}</button></div></form></div>"""
