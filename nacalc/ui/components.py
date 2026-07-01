"""Small, reusable render helpers for the dashboard (formatting, phase dots,
bars, status cell). Pure functions — no IO. Used by nacalc/ui/pages.py."""
from html import escape as esc

from ..i18n import t


def eur(n):
    if n is None:
        return "—"
    n = int(round(n))
    s = f"{abs(n):,}".replace(",", ".")
    return ("-€" if n < 0 else "€") + s

def h1(n):
    return ("%.1f" % (n or 0))

def _dot(p):
    if not p["applicable"]:
        cls = "c-none"
    elif not p["started"]:
        cls = "c-todo"
    else:
        cls = {"green": "c-good", "amber": "c-warn", "red": "c-over", "darkred": "c-crit"}.get(p["color"], "c-good")
    state = {"done": "st-done", "progress": "st-progress"}.get(p["glyph"], "")
    if p["applicable"] and p["started"]:
        title = f'{p["naam"]}: {p["tracked_hours"]}/{p["budget_hours"]}u ({p["pct"]}%)'
    elif not p["applicable"]:
        title = f'{p["naam"]}: n/a'
    else:
        title = f'{p["naam"]}: 0/{p["budget_hours"]}u'
    return f'<span class="pdot {cls} {state}" title="{esc(title)}"></span>'

def dots(phases):
    return '<div class="phases">' + "".join(_dot(p) for p in phases) + "</div>"

def bar_color(color):
    return {"green": "var(--green)", "amber": "var(--amber)", "red": "var(--red)",
            "darkred": "var(--darkred)", "none": "var(--grey)"}.get(color, "var(--green)")

def _uren_ratio_color(r):
    if r > 1.15:
        return "var(--darkred)"
    if r > 1:
        return "var(--red)"
    if r >= 0.8:
        return "var(--amber)"
    return "var(--green)"

def _status_cell(lang, snap):
    s = snap["summary_status"]
    if s == "over":
        ic, cls, ti, su = "!", "over", t("st_over", lang), f'{snap["n_over"]} {t("phases_over",lang)}'
    elif s == "warn":
        ic, cls, ti, su = "⚠", "warn", t("st_warn", lang), f'{snap["n_warn"]} {t("phases_warn",lang)}'
    elif s == "ok":
        ic, cls, ti, su = "✓", "ok", t("st_ok", lang), t("st_within", lang)
    else:
        ic, cls, ti, su = "·", "none", t("st_notstarted", lang), ""
    return cls, (f'<div class="st-cell"><div class="st-ic {cls}">{ic}</div>'
                 f'<div class="st-tx"><b>{esc(ti)}</b><span>{esc(su)}</span></div></div>')

def _abar(name, width, label, color, title=""):
    """One analysis bar. width = fill 0-100; label = text shown; title = hover tooltip."""
    return (f'<div class="arow" title="{esc(title)}"><div class="an">{esc(str(name))}</div>'
            f'<div class="abar"><i style="width:{min(max(width,0),100):.0f}%;background:{color}">{esc(label)}</i></div>'
            f'<div class="av">{esc(label)}</div></div>')
