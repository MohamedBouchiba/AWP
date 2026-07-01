"""Server-rendered dashboard pages (Dutch/English). The dashboard CSS lives in
assets/css/dashboard.css and is inlined at import time (identical output to the
previous inline <style> block) — edit that .css file to restyle the dashboard.
Data comes from nacalc/views.py; formatting helpers from nacalc/ui/components.py."""
import os
from html import escape as esc

from ..i18n import t
from .components import (eur, h1, dots, bar_color, _uren_ratio_color,
                        _status_cell, _abar)

_CSS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "css")


def _load_css(name):
    with open(os.path.join(_CSS_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


STYLE = "<style>" + _load_css("dashboard.css") + "</style>"


def shell(lang, active, title, sub, content, badge, synced_text, syncing, is_admin, collapsed=False):
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
        pill = f'<span class="pill" id="syncPill"><span class="dot" style="background:var(--amber)"></span> {esc(t("syncing",lang))}</span>'
    else:
        pill = f'<span class="pill" id="syncPill"><span class="dot"></span> {esc(synced_text)}</span>'

    def _mob(view, key, extra=""):
        cls = "active" if active == view else ""
        return f'<a class="{cls}" href="/app/{view}">{esc(t(key,lang))}{extra}</a>'
    mob_badge = f' <span class="badge">{badge}</span>' if badge else ""
    mobnav = (f'<nav class="mobnav">{_mob("overzicht","nav_overzicht")}{_mob("meldingen","nav_meldingen",mob_badge)}'
              f'{_mob("analyse","nav_analyse")}{(_mob("beheer","nav_beheer") if is_admin else "")}</nav>')
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
function applyFilters(){{var c=v('fCat'),ct=v('fCon'),st=v('fSt'),q=(v('fSearch')||'').toLowerCase(),g=v('fGestart');
document.querySelectorAll('#rows tr').forEach(function(tr){{var d=tr.dataset;var ok=(!c||d.cat===c)&&(!ct||d.con===ct)&&(!st||d.st===st)&&(!q||(d.search||'').indexOf(q)>=0)&&(g!=='ja'||d.status!=='0');tr.style.display=ok?'':'none';}});}}
function v(id){{var e=document.getElementById(id);return e?e.value:'';}}
function sortTable(key,numeric){{var tb=document.getElementById('rows');if(!tb)return;var rows=[].slice.call(tb.querySelectorAll('tr'));var same=tb.getAttribute('data-sk')===key&&tb.getAttribute('data-sd')==='1';var dir=same?-1:1;rows.sort(function(a,b){{var x=a.dataset[key]||'',y=b.dataset[key]||'';if(numeric){{return ((parseFloat(x)||0)-(parseFloat(y)||0))*dir;}}return String(x).localeCompare(String(y))*dir;}});rows.forEach(function(r){{tb.appendChild(r);}});tb.setAttribute('data-sk',key);tb.setAttribute('data-sd',dir===1?'1':'0');}}
function toggleSidebar(){{var a=document.querySelector('.app');var c=a.classList.toggle('collapsed');document.cookie='sidebar='+(c?'collapsed':'open')+';path=/;max-age=31536000;samesite=Lax';}}
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeDrawer();}});
var SYNCING={"true" if syncing else "false"};
if(SYNCING){{poll();}}
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

def render_overzicht(lang, snaps, kpis, cats, cons, syncing=False, show_rates_banner=False):
    import json
    if not snaps:
        if syncing:
            return (f'<div class="state"><div class="sp"></div>'
                    f'<h3>{esc(t("first_sync",lang))}</h3><p>{esc(t("first_sync_sub",lang))}</p></div>')
        return f'<div class="state"><h3>{esc(t("empty_nodata",lang))}</h3></div>'
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
              f'<span class="li"><span class="pdot c-todo"></span> {esc(t("lg_todo",lang))}</span></div>')
    rows = []
    for s in snaps:
        phases = json.loads(s["phases_json"] or "[]")
        begroot = s["uren_begroot"] or 0
        gepr = s["uren_gepresteerd"] or 0
        r = gepr / begroot if begroot else 0
        rowcls, stcell = _status_cell(lang, s)
        marge = s["marge"]
        if marge is not None:
            marge_chip = f'<span class="marge-chip {"pos" if marge >= 0 else "neg"}">{eur(marge)}</span>'
        else:
            marge_chip = f'<span style="color:var(--muted)" title="{esc(t("rates_missing",lang))}">—</span>'
        sub = esc(s["adres"] or s["categorie"] or "")
        search = esc(" ".join(str(x) for x in [s["project_key"], s["naam"], s["adres"],
                     s["verantw_arch"]] if x).lower())
        rows.append(
            f'<tr class="row-{rowcls}" data-cat="{esc(s["categorie"] or "")}" data-con="{esc(s["contracttype"] or "")}"'
            f' data-st="{ {"over":"over","warn":"warn","ok":"ok","none":""}[s["summary_status"]] }" data-search="{search}"'
            f' data-status="{rank.get(s["summary_status"],0)}" data-offerte="{s["offerte_awp"] or 0}"'
            f' data-marge="{marge if marge is not None else 0}" data-pct="{r*100:.0f}" data-nr="{esc(s["project_key"] or "")}"'
            f' onclick="openDrawer(\'{s["project_id"]}\')">'
            f'<td>{stcell}</td>'
            f'<td><div class="pcell"><span class="pkey">{esc(s["project_key"] or "—")}</span>'
            f'<div class="pname">{esc(s["naam"] or "")}</div><div class="psub">{sub}</div></div></td>'
            f'<td class="who"><b>{esc(s["verantw_arch"] or "—")}</b><span>{esc(s["verantw_medewerker"] or "")}</span></td>'
            f'<td><span class="tag">{esc(s["categorie"] or "—")}</span></td>'
            f'<td><span class="tag">{esc(s["contracttype"] or "—")}</span></td>'
            f'<td class="num">{eur(s["budget_klant"])}</td>'
            f'<td class="num">{eur(s["offerte_awp"])}</td>'
            f'<td><div class="bar"><i style="width:{min(r*100,100):.0f}%;background:{_uren_ratio_color(r)}"></i></div>'
            f'<div class="barlab">{h1(gepr)} / {h1(begroot)}u · {(f"{r*100:.0f}%" if begroot else "—")}</div></td>'
            f'<td>{dots(phases)}</td>'
            f'<td class="num">{marge_chip}</td></tr>')
    body = "".join(rows) or (f'<tr><td colspan="10" style="text-align:center;color:var(--muted);padding:30px">{esc(t("no_projects",lang))}</td></tr>')
    return f"""{banner}<div class="kpis">{kpi_html}</div>
<div class="filters">
<div class="search"><input id="fSearch" oninput="applyFilters()" placeholder="{esc(t('f_search',lang))}"></div>
<select id="fCat" onchange="applyFilters()"><option value="">{esc(t('f_all_cat',lang))}</option>{cat_opts}</select>
<select id="fCon" onchange="applyFilters()"><option value="">{esc(t('f_all_con',lang))}</option>{con_opts}</select>
<select id="fSt" onchange="applyFilters()"><option value="">{esc(t('f_all_st',lang))}</option>
<option value="over">{esc(t('f_over',lang))}</option><option value="warn">{esc(t('f_warn',lang))}</option><option value="ok">{esc(t('f_ok',lang))}</option></select>
<select id="fGestart" onchange="applyFilters()"><option value="">{esc(t('f_started_all',lang))}</option><option value="ja">{esc(t('f_started_only',lang))}</option></select>
<span class="pill type-pill">{esc(t('type_arch',lang))}</span></div>
{legend}
<div class="card"><div class="tablewrap"><table><thead><tr>
<th class="sortable" onclick="sortTable('status',1)">{esc(t('th_status',lang))}<span class="ar">⇅</span></th>
<th class="sortable" onclick="sortTable('nr',0)">{esc(t('th_project',lang))}<span class="ar">⇅</span></th>
<th>{esc(t('th_owner',lang))}</th><th>{esc(t('th_cat',lang))}</th><th>{esc(t('th_con',lang))}</th>
<th class="num">{esc(t('th_budget_klant',lang))}</th>
<th class="num sortable" onclick="sortTable('offerte',1)">{esc(t('th_offerte',lang))}<span class="ar">⇅</span></th>
<th class="sortable" onclick="sortTable('pct',1)">{esc(t('th_uren',lang))}<span class="ar">⇅</span></th>
<th>{esc(t('th_fases',lang))}</th>
<th class="num sortable" onclick="sortTable('marge',1)">{esc(t('th_marge',lang))}<span class="ar">⇅</span></th>
</tr></thead><tbody id="rows">{body}</tbody></table></div></div>
<div class="foot-note">{esc(t('ov_foot',lang))}</div>"""

def render_drawer(lang, s):
    import json
    phases = json.loads(s["phases_json"] or "[]")
    chip_map = {"over": ("c-over", t("st_over", lang)), "warn": ("c-warn", t("st_warn", lang)),
                "ok": ("c-ok", t("st_ok", lang)), "none": ("", t("st_notstarted", lang))}
    chipcls, chiptx = chip_map.get(s["summary_status"], ("", ""))
    fase_rows = []
    for p in phases:
        if not p["applicable"]:
            fase_rows.append(f'<div class="fase-row" style="opacity:.55"><div class="fr-top">'
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
            f'<div class="fr-meta"><span>{eur(p["spent_eur"])} / {eur(p["budget_eur"])} verbruikt</span><span>{p["pct"] if p["pct"] is not None else 0}%</span></div></div>')
    note = ""  # "Aandachtspunt" note removed per request
    kost_html = eur(s["effectieve_kost"]) if s["effectieve_kost"] is not None else f'<span style="font-size:12px;color:var(--muted)">{esc(t("rates_missing",lang))}</span>'
    est = f' <span style="font-size:11px;color:var(--muted)">{esc(t("estimate_flag",lang))}</span>' if s["cost_estimated"] else ""
    marge_html = (f'{eur(s["marge"])} · {s["marge_pct"]}%' if s["marge"] is not None else "—")
    marge_col = "var(--green)" if (s["marge"] or 0) >= 0 else "var(--red)"
    return f"""<div class="dr-head"><button class="x" onclick="closeDrawer()">×</button>
<h2>{esc(s["project_key"] or "")} · {esc(s["naam"] or "")}</h2>
<div class="m">{esc(s["adres"] or "")} &nbsp;•&nbsp; {esc(s["verantw_arch"] or "")}</div>
<div style="margin-top:10px;display:flex;gap:8px;align-items:center"><span class="tag">{esc(s["categorie"] or "—")}</span>
<span class="tag">{esc(s["contracttype"] or "—")}</span><span class="status-chip {chipcls}" style="font-weight:700;font-size:12px;padding:4px 10px;border-radius:20px">● {esc(chiptx)}</span></div></div>
<div class="dr-body"><div class="meta-grid">
<div class="mc"><div class="l">{esc(t('dr_budget_klant',lang))}</div><div class="v">{eur(s["budget_klant"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_raming',lang))}</div><div class="v">{eur(s["raming_vo"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_offerte',lang))}</div><div class="v">{eur(s["offerte_awp"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_uren',lang))}</div><div class="v">{h1(s["uren_gepresteerd"])} / {h1(s["uren_begroot"])}</div></div>
<div class="mc"><div class="l">{esc(t('dr_kost',lang))}</div><div class="v">{kost_html}{est}</div></div>
<div class="mc"><div class="l">{esc(t('dr_marge',lang))}</div><div class="v" style="color:{marge_col}">{marge_html}</div></div>
</div>
<div class="sec-t">{esc(t('dr_voortgang',lang))}</div>{"".join(fase_rows)}
<div style="font-size:11px;color:var(--muted);margin-top:4px;line-height:1.4">{esc(t('ph_caption',lang))}</div>{note}
<div class="sec-t">{esc(t('dr_visits',lang))}</div><div class="meta-grid">
<div class="mc"><div class="l">{esc(t('dr_werfbezoek',lang))}</div><div class="v">{s["werfbezoeken"] or 0}</div></div>
<div class="mc"><div class="l">{esc(t('dr_bespreking',lang))}</div><div class="v">{s["besprekingen"] or 0}</div></div>
</div></div>"""

def render_meldingen(lang, items):
    if not items:
        return f'<p class="panel-s" style="margin-bottom:18px">{esc(t("ml_sub",lang))}</p><div class="card" style="padding:30px;text-align:center;color:var(--muted)">{esc(t("ml_empty",lang))}</div>'
    out = [f'<p class="panel-s" style="margin-bottom:18px">{esc(t("ml_sub",lang))}</p>']
    for m in items:
        over = m["severity"] in ("red", "darkred")
        col = "var(--red)" if over else "var(--amber)"
        out.append(
            f'<div class="alert"><div class="ai {"ai-over" if over else "ai-warn"}">{"🔴" if over else "🟠"}</div>'
            f'<div><div class="at">{esc(m["project_key"] or "")} · {esc(m["naam"] or "")} — {esc(t("ml_phase",lang))} {esc(m["phase_naam"] or "")}</div>'
            f'<div class="ad">{esc(t("ml_over",lang) if over else t("ml_warn",lang))} · {m["pct"]}%</div></div>'
            f'<div class="ax"><div class="pct" style="color:{col}">{m["pct"]}%</div>'
            f'<button class="btn" onclick="openDrawer(\'{m["project_id"]}\')">{esc(t("ml_view",lang))} →</button></div></div>')
    return "".join(out)

def render_analyse(lang, fases, contracts, cats, raming):
    def panel(tk, sk, ik, inner):
        return (f'<div class="card" style="padding:20px 22px"><p class="panel-t">{esc(t(tk,lang))}'
                f'<span class="pinfo" title="{esc(t(ik,lang))}">i</span></p>'
                f'<p class="panel-s">{esc(t(sk,lang))}</p>{inner or "<p class=\'panel-s\'>"+esc(t("an_empty",lang))+"</p>"}</div>')

    # 1) Budget used per phase: bar = % consumed, FULL at >=100% (over budget).
    f_html = ""
    for naam, pct, n in fases:
        color = "var(--red)" if pct >= 100 else "var(--amber)" if pct >= 80 else "var(--green)"
        tip = t("an_tip_fase", lang).format(naam=naam, pct=pct, n=n)
        f_html += _abar(naam, min(pct, 100), f"{pct}%", color, tip)

    # 2) Profitability per contract type: bar = margin magnitude (scaled to 80).
    c_html = ""
    for naam, pct, n in contracts:
        color = "var(--green)" if pct > 40 else "var(--amber)" if pct > 20 else "var(--red)"
        tip = t("an_tip_con", lang).format(naam=naam, pct=pct, n=n)
        c_html += _abar(naam, abs(pct) / 80 * 100, f"{'+' if pct >= 0 else ''}{pct}%", color, tip)

    # 3) Over-budget share per category: bar = % of projects over budget.
    cat_html = ""
    for naam, pct, n, n_over in cats:
        color = "var(--red)" if pct > 50 else "var(--amber)" if pct > 0 else "var(--green)"
        tip = t("an_tip_cat", lang).format(naam=naam, pct=pct, n=n, n_over=n_over)
        cat_html += _abar(naam, pct, f"{pct}%", color, tip)

    # 4) Projects with a client budget: over/on-track status.
    r_html = ""
    for nr, over, budget in raming:
        status = t("st_over", lang) if over else t("st_ok", lang)
        tip = t("an_tip_raming", lang).format(budget=eur(budget), status=status)
        col = "var(--red)" if over else "var(--accent)"
        bg = "var(--red-bg)" if over else "var(--grey-bg)"
        r_html += (f'<div class="arow" title="{esc(tip)}"><div class="an">{esc(nr)}</div>'
                   f'<div class="abar" style="background:{bg}"><i style="width:{85 if over else 55}%;background:{col}">{esc(status)}</i></div>'
                   f'<div class="av">{"⚠" if over else "✓"}</div></div>')

    return (f'<p class="panel-s" style="margin-bottom:18px">{esc(t("an_sub",lang))}</p><div class="grid2">'
            + panel("an_fases_t", "an_fases_s", "an_info_fase", f_html) + panel("an_con_t", "an_con_s", "an_info_con", c_html)
            + panel("an_cat_t", "an_cat_s", "an_info_cat", cat_html) + panel("an_raming_t", "an_raming_s", "an_info_raming", r_html) + "</div>")

def render_beheer(lang, users, thresholds, internal_rate, external_rate, saved):
    msg = f'<div class="savemsg">{esc(t("be_saved",lang))}</div>' if saved else ""
    user_rows = "".join(
        f'<div class="be-row"><span class="nm">{esc(u["naam"] or u["email"])}</span>'
        f'<span style="color:var(--muted);font-size:12px">{esc(u["email"])}</span>'
        f'{"<span class=tag>"+esc(t("be_admin",lang))+"</span>" if u["is_admin"] else ""}</div>' for u in users)
    th = thresholds
    return f"""{msg}
<div class="be-card"><h2>{esc(t('be_rates_title',lang))}</h2>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="rates">
<div class="be-row"><span class="nm">{esc(t('be_internal_cost',lang))}</span><input name="internal_cost_rate" type="number" step="0.01" value="{internal_rate}" style="width:120px"> €/u</div>
<div class="be-row"><span class="nm">{esc(t('be_external_rate',lang))}</span><input name="external_rate" type="number" step="0.01" value="{external_rate}" style="width:120px"> €/u</div>
<button class="btn" style="margin-top:14px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button></form></div>
<div class="be-card"><h2>{esc(t('be_thresholds',lang))}</h2>
<form method="post" action="/app/beheer"><input type="hidden" name="form" value="thresholds">
<div class="be-row">amber ≥ <input name="amber" type="number" value="{th['amber']}" style="width:80px"> %
&nbsp; red &gt; <input name="red" type="number" value="{th['red']}" style="width:80px"> %
&nbsp; dark-red ≥ <input name="darkred" type="number" value="{th['darkred']}" style="width:80px"> %</div>
<button class="btn" style="margin-top:8px;background:var(--accent);color:#fff;border:none" type="submit">{esc(t('be_save',lang))}</button></form></div>
<div class="be-card"><h2>{esc(t('be_users',lang))}</h2>{user_rows}
<form method="post" action="/app/beheer" style="margin-top:14px"><input type="hidden" name="form" value="adduser">
<div class="be-row"><input name="naam" placeholder="Naam" required><input name="email" type="email" placeholder="E-mail" required>
<input name="password" type="password" placeholder="Wachtwoord" required>
<label style="font-size:12px"><input type="checkbox" name="is_admin"> {esc(t('be_admin',lang))}</label>
<button class="btn" type="submit">{esc(t('be_add_user',lang))}</button></div></form></div>"""
