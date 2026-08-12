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

def hb(n):
    """Hours-or-dash: Teamleader often has no time budget on a phase -> show '—',
    never a misleading '0.0'."""
    return "—" if not n else h1(n)


# ---------- the single margin gate ----------
# Margin = invoiced - effective cost. It is meaningless (and misleading) when
# nothing is invoiced yet: a pre-migration snapshot still carries the OLD margin
# (offerte - cost) while `gefactureerd` is NULL. Everything that displays a
# margin -- drawer, overview chip, sort key, KPI, export -- must go through here
# so they can never drift apart.
def invoiced_total(s):
    """Everything invoiced: Teamleader + what was invoiced outside it.

    Client: "Niet alle facturen van dit project werden via Teamleader gestuurd.
    Zijn er mogelijkheden om dit ergens manueel toe te voegen?" -- so an admin
    can type the missing amount in the drawer and every derived figure follows.
    """
    return round((s.get("gefactureerd") or 0) + (s.get("gefactureerd_manueel") or 0), 2)


def invoiced(s):
    """True when the project has a positive invoiced amount. The ONE definition
    of 'a margin is meaningful here' -- also used by the profitability graphs, so
    a negative net (credit note > invoice) can't slip into one view but not another."""
    return invoiced_total(s) > 0


def visible_marge(s):
    """Margin computed LIVE from what is on the row, never from the stored value.

    The stored `marge` is written by the sync, so a manually-entered invoice (or
    a snapshot from before the definition changed) leaves it stale -- that was
    the A371 bug, where a row kept an old "offerte - kost" margin while
    gefactureerd was still NULL. Deriving it here makes that class of bug
    structurally impossible.
    """
    if not invoiced(s):
        return None
    kost = s.get("effectieve_kost")
    if kost is None:
        return None
    return round(invoiced_total(s) - kost, 2)


def visible_marge_pct(s):
    m = visible_marge(s)
    if m is None:
        return None
    basis = invoiced_total(s)
    return round(m / basis * 100) if basis else 0


def xl_safe(v):
    """Neutralise spreadsheet formula injection in exported text cells."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s

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
        title = f'{p["naam"]}: niet inbegrepen'
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
