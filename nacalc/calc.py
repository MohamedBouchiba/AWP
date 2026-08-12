"""Pure computation for the nacalculatie dashboard (no IO -> unit-testable).

Per-phase status is driven by Teamleader's per-group MONEY fields:
  pct = external_budget_spent / external_budget. Hours per phase are REAL
  (group time_tracked / time_estimated, quotation hours as budget fallback);
  billed_eur / cost_eur come from the group's amount_billed / cost (None when
  the 'Costs on projects' permission hides them).
Color = budget status; glyph = progress.
"""
from . import phases as phases_mod   # pure module too -- no IO, no cycle

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


def _money_or_none(v):
    return round(float(v), 2) if v is not None else None


def build_phases(raw_phases, thresholds, taxonomy=None):
    """raw_phases: list of {name, budget_eur, spent_eur, budget_hours,
    tracked_hours, billed_eur, cost_eur} (any order; last three optional).

    Returns ordered list of phase dicts with pct/color/glyph/flags computed.

    Rows stay in the PROJECT's own order (leading number) -- that is what the
    drawer shows. `taxonomy` only annotates each phase with its cross-project
    identity (canon/order/overhead) so the analysis can regroup and the rollup
    can skip overhead; it never reorders the project's own phases.
    """
    rows = sorted(raw_phases, key=lambda p: _phase_sort_key(p.get("name")))
    out = []
    for p in rows:
        be = float(p.get("budget_eur") or 0)
        se = float(p.get("spent_eur") or 0)
        bh = float(p.get("budget_hours") or 0)
        th = float(p.get("tracked_hours") or 0)   # REAL hours (group time_tracked)
        applicable = be > 0
        pct = round(se / be * 100, 1) if be > 0 else None
        # Started = money consumed OR hours logged (hours can precede the first
        # simulated-spend rollup, and this is the feedback's definition).
        started = se > 0 or th > 0
        cn = phases_mod.canonical(p.get("name"), taxonomy)
        out.append({
            "naam": p.get("name"),
            # Cross-project identity, persisted in phases_json so the analysis
            # and the alerts read the same answer the sync computed.
            "canon": cn["key"],
            "canon_label": cn["label"],
            "canon_order": cn["order"],
            "overhead": cn["overhead"],
            "budget_eur": round(be, 2),
            "spent_eur": round(se, 2),
            "budget_hours": round(bh, 1),
            "tracked_hours": round(th, 1),
            "billed_eur": _money_or_none(p.get("billed_eur")),
            "cost_eur": _money_or_none(p.get("cost_eur")),
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


def _rankable(phases):
    """_active minus overhead phases.

    Client feedback: "Het onderdeel administratie moet niet mee opgenomen worden
    in de toggle dreigt over te gaan. Technisch gezien registreren we amper iets
    op dit onderdeel, dit is een overheadskost." A €250 admin budget goes over
    100% on the first hour booked and drags the whole project red.

    Deliberately NOT applied to project_totals(): overhead is still real work
    with a real time budget, so it keeps counting in the hours bar. Only the
    budget-status rollup ignores it.
    """
    return [p for p in _active(phases) if not p.get("overhead")]


def project_summary(phases):
    """Strictest budget status over started, budgeted, non-overhead phases."""
    active = _rankable(phases)
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


def margin(basis_eur, kost_eur):
    """Marge = basis − effectieve kost, met pct t.o.v. de basis.
    Basis = gefactureerd (feedback ronde 2); voorheen de offerte."""
    basis = float(basis_eur or 0)
    kost = float(kost_eur or 0)
    marge = round(basis - kost, 2)
    marge_pct = round(marge / basis * 100) if basis else 0
    return marge, marge_pct
