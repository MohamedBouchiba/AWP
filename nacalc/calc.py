"""Pure computation for the nacalculatie dashboard (no IO -> unit-testable).

Per-phase status is driven by Teamleader's reliable per-group MONEY fields:
  pct = external_budget_spent / external_budget  (rate cancels, so this equals
  the hours-consumption ratio). Budget HOURS per phase come from the quotation
  section quantities. Tracked hours per phase = pct * budget_hours.
Color = budget status; glyph = progress. Mirrors the approved prototype logic.
"""

SEVERITY_ORDER = ["green", "amber", "red", "darkred"]


def color_for(pct, thresholds):
    """Map a consumption percentage to a budget-status color."""
    if pct is None:
        return "none"
    if pct >= thresholds["darkred"]:
        return "darkred"
    if pct > thresholds["red"]:
        return "red"
    if pct >= thresholds["amber"]:
        return "amber"
    return "green"


def _phase_sort_key(name):
    """Order phases by their leading number ('1. ADMINISTRATIE' -> 1); others last."""
    head = (name or "").strip().split(".", 1)[0]
    try:
        return (0, int(head))
    except (ValueError, TypeError):
        return (1, name or "")


def build_phases(raw_phases, thresholds):
    """raw_phases: list of {name, budget_eur, spent_eur, budget_hours} (any order).

    Returns ordered list of phase dicts with pct/color/glyph/flags computed.
    """
    rows = sorted(raw_phases, key=lambda p: _phase_sort_key(p.get("name")))
    out = []
    for p in rows:
        be = float(p.get("budget_eur") or 0)
        se = float(p.get("spent_eur") or 0)
        bh = float(p.get("budget_hours") or 0)
        applicable = be > 0
        pct = round(se / be * 100, 1) if be > 0 else None
        started = se > 0
        tracked_hours = round((pct or 0) / 100 * bh, 1) if applicable else 0.0
        out.append({
            "naam": p.get("name"),
            "budget_eur": round(be, 2),
            "spent_eur": round(se, 2),
            "budget_hours": round(bh, 1),
            "tracked_hours": tracked_hours,
            "pct": pct,
            "color": color_for(pct, thresholds),
            "applicable": applicable,
            "started": started,
            "done": False,      # filled below
            "glyph": "none",    # filled below
        })
    # progress: a phase is 'done' when it has work AND a LATER phase has work too.
    for i, ph in enumerate(out):
        later_started = any(x["started"] for x in out[i + 1:])
        ph["done"] = bool(ph["started"] and later_started)
        if not ph["applicable"]:
            ph["glyph"] = "none"
        elif not ph["started"]:
            ph["glyph"] = "not_started"
        elif ph["done"]:
            ph["glyph"] = "done"
        else:
            ph["glyph"] = "progress"
    return out


def _active(phases):
    """Started phases that have a budget (color is rankable). A started phase
    with no budget (e.g. unquoted meerwerken/regie) is shown but excluded from
    the budget-status rollup -- it's extra work, not a budget overrun."""
    return [p for p in phases if p["started"] and p["applicable"] and p["color"] in SEVERITY_ORDER]


def project_summary(phases):
    """Strictest budget status over started, budgeted phases, with counts."""
    active = _active(phases)
    if not active:
        return {"status": "none", "n_over": 0, "n_warn": 0, "started_count": 0}
    worst = "green"
    for p in active:
        if SEVERITY_ORDER.index(p["color"]) > SEVERITY_ORDER.index(worst):
            worst = p["color"]
    n_over = sum(1 for p in active if p["color"] in ("red", "darkred"))
    n_warn = sum(1 for p in active if p["color"] == "amber")
    status = "over" if worst in ("red", "darkred") else ("warn" if worst == "amber" else "ok")
    return {"status": status, "n_over": n_over, "n_warn": n_warn,
            "started_count": len(active)}


def project_totals(phases):
    """Sum budget/tracked hours over started, budgeted phases (so unstarted future
    budget doesn't dwarf the progress bar), plus the grand totals."""
    active = _active(phases)
    return {
        "begroot_uren_aangesneden": round(sum(p["budget_hours"] for p in active), 1),
        "gepresteerd_uren": round(sum(p["tracked_hours"] for p in active), 1),
        "begroot_uren_totaal": round(sum(p["budget_hours"] for p in phases), 1),
    }


def margin(offerte_eur, kost_eur):
    """Marge = offerte - effectieve kost (mirrors prototype/spec)."""
    offerte = float(offerte_eur or 0)
    kost = float(kost_eur or 0)
    marge = round(offerte - kost, 2)
    marge_pct = round(marge / offerte * 100) if offerte else 0
    return marge, marge_pct
