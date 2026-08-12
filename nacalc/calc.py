"""Pure computation for the nacalculatie dashboard (no IO -> unit-testable).

Per-phase status is driven by Teamleader's per-group MONEY fields:
  pct = external_budget_spent / external_budget. Hours per phase are REAL
  (group time_tracked / time_estimated, quotation hours as budget fallback);
  billed_eur / cost_eur come from the group's amount_billed / cost (None when
  the 'Costs on projects' permission hides them).
Color = budget status; glyph = progress.
"""
from . import config                 # constants only -- no IO
from . import phases as phases_mod   # pure module too -- no IO, no cycle

SEVERITY_ORDER = ["green", "amber", "red", "darkred"]

# What the per-phase percentage measures.
#   "cost"  = kostprijs bureau / geofferteerd budget  (default since 2026-08)
#   "spent" = Teamleader's external_budget_spent / external_budget  (legacy)
#
# Why the switch (client feedback + the A346 probe): external_budget_spent is
# NOT what was invoiced -- dividing it by the phase's tracked hours gives
# €85-90/h, i.e. Teamleader values the hours at the SELLING rate. Comparing a
# selling-rate figure to the quoted budget makes every phase look worse than it
# is. What the office actually wants to know is "what did this phase cost us
# against what we quoted for it", which is cost / external_budget -- the same
# pair Teamleader itself uses for its own `margin` field (price - cost).
BASIS_COST = "cost"
BASIS_SPENT = "spent"
DEFAULT_BASIS = BASIS_COST


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


def phase_cost(p, internal_rate=None):
    """(cost €, source) of one phase — the per-phase twin of sync's cascade.

    1. Teamleader's own `cost` on the group (real, per person, historically
       correct) when the 'Costs on projects' permission exposes it;
    2. tracked hours × the internal rate, when it doesn't;
    3. (None, None) when we know neither — never a fake €0.
    """
    c = p.get("cost_eur")
    if c is not None:
        return round(float(c), 2), "teamleader"
    th = float(p.get("tracked_hours") or 0)
    if th > 0 and internal_rate:
        return round(th * float(internal_rate), 2), "flat"
    return None, None


def build_phases(raw_phases, thresholds, taxonomy=None, basis=DEFAULT_BASIS,
                 internal_rate=None):
    """raw_phases: list of {name, budget_eur, spent_eur, budget_hours,
    tracked_hours, billed_eur, cost_eur} (any order; last three optional).

    Returns ordered list of phase dicts with pct/color/glyph/flags computed.

    Rows stay in the PROJECT's own order (leading number) -- that is what the
    drawer shows. `taxonomy` only annotates each phase with its cross-project
    identity (canon/order/overhead) so the analysis can regroup and the rollup
    can skip overhead; it never reorders the project's own phases.

    `basis` picks the numerator of the percentage (see BASIS_* above).
    `verbruikt_eur` always carries the number the percentage was computed from,
    so the UI can show the figure it is actually judging -- never a percentage
    over one number next to a different number in euros.
    """
    rows = sorted(raw_phases, key=lambda p: _phase_sort_key(p.get("name")))
    out = []
    for p in rows:
        be = float(p.get("budget_eur") or 0)
        se = float(p.get("spent_eur") or 0)
        bh = float(p.get("budget_hours") or 0)
        th = float(p.get("tracked_hours") or 0)   # REAL hours (group time_tracked)
        applicable = be > 0
        kost, kost_bron = phase_cost(p, internal_rate)
        if basis == BASIS_COST:
            verbruikt = kost
        else:
            verbruikt, kost_bron = se, "spent"
        pct = round(verbruikt / be * 100, 1) if (be > 0 and verbruikt is not None) else None
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
            "cost_eur": _money_or_none(kost),
            "kost_bron": kost_bron,
            "basis": basis,
            "verbruikt_eur": _money_or_none(verbruikt),
            "pct": pct,
            # Hours ratio, alongside the euro ratio. Gated on budget_hours (a
            # TIME budget), deliberately not on `applicable`, which tests the
            # euro budget -- a phase can have one without the other.
            "uren_pct": round(th / bh * 100, 1) if bh > 0 else None,
            "uren_color": color_for(round(th / bh * 100, 1) if bh > 0 else None, thresholds),
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


def _uren_pct(p):
    """Hours worked over hours budgeted, or None when there is no time budget.

    Recomputed rather than read from the stored `uren_pct`, so snapshots written
    before this field existed still produce a correct status.
    """
    bh = p.get("budget_hours") or 0
    if not bh:
        return None
    return round((p.get("tracked_hours") or 0) / bh * 100, 1)


def project_summary(phases, thresholds=None):
    """Project status, driven by HOURS worked against hours budgeted.

    Client rule (Michiel, 2026-08-12): the project label follows the hours, not
    the euros. Two measures, and the worst one wins:

      actief  the phase currently in progress, against its OWN budgeted hours;
      cumul   Σ tracked / Σ budgeted over the started, budgeted, non-overhead
              phases — "previous + active phases" taken together.

    "you look at the current phase OR if the total is over budget". A finished
    phase that overran does NOT keep the project flagged on its own: Michiel was
    explicit that once a later phase starts and the total is back within budget,
    the project reads ok again. Its overrun stays visible on the phase itself.

    The per-phase euro percentage (cost vs quoted budget) is untouched: it still
    drives the phase dots, the drawer and both analyses. Only the project badge
    moved to hours.

    Note the 115% threshold never affected this badge and still does not — red
    and darkred both collapse into "over" below; 115% only colours a phase dot.
    """
    thresholds = thresholds or config.DEFAULT_THRESHOLDS
    active = _rankable(phases)
    if not active:
        # Nothing left to judge. Two very different situations hide here, and
        # collapsing them into "Nog niet gestart" was wrong: on 26 of AWP's
        # projects the ONLY started, budgeted phase is administratie, so
        # excluding overhead emptied the rollup and declared live projects
        # not started -- while their phase dot was red and the "enkel gestarte"
        # filter still listed them.
        # Overhead running on its own means the real work has not consumed any
        # quoted budget yet, which is "op koers", not "not started".
        if _active(phases):
            return {"status": "ok", "n_over": 0, "n_warn": 0, "started_count": 0,
                    "uren_pct": None, "basis": "overhead"}
        return {"status": "none", "n_over": 0, "n_warn": 0, "started_count": 0,
                "uren_pct": None, "basis": None}
    # Only phases that actually carry a time budget can be judged on hours;
    # including the others would add worked hours with nothing to divide by.
    timed = [p for p in active if (p.get("budget_hours") or 0) > 0]
    if not timed:
        # No hours information at all. Rather than report a flattering "op
        # koers", fall back to the euro rollup so the project keeps a signal.
        worst = "green"
        for p in active:
            if SEVERITY_ORDER.index(p["color"]) > SEVERITY_ORDER.index(worst):
                worst = p["color"]
        return {"status": ("over" if worst in ("red", "darkred")
                           else "warn" if worst == "amber" else "ok"),
                "n_over": sum(1 for p in active if p["color"] in ("red", "darkred")),
                "n_warn": sum(1 for p in active if p["color"] == "amber"),
                "started_count": len(active), "uren_pct": None, "basis": "euro"}

    budg = sum(p.get("budget_hours") or 0 for p in timed)
    trak = sum(p.get("tracked_hours") or 0 for p in timed)
    cumul = round(trak / budg * 100, 1) if budg > 0 else None
    # The phase in progress is the last started one: build_phases marks every
    # earlier started phase "done", so there is at most one "progress".
    actief = next((_uren_pct(p) for p in timed if p.get("glyph") == "progress"), None)
    worst_pct = max([x for x in (cumul, actief) if x is not None], default=None)
    worst = color_for(worst_pct, thresholds)
    # Counts follow the same measure as the badge, so "2 fasen over budget"
    # cannot contradict the label above it. Derived here rather than read from
    # uren_color, so a snapshot written before this rule existed still works.
    cols = [color_for(_uren_pct(p), thresholds) for p in timed]
    n_over = sum(1 for c in cols if c in ("red", "darkred"))
    n_warn = sum(1 for c in cols if c == "amber")
    status = "over" if worst in ("red", "darkred") else ("warn" if worst == "amber" else "ok")
    return {"status": status, "n_over": n_over, "n_warn": n_warn,
            "started_count": len(timed), "uren_pct": worst_pct, "basis": "uren"}


def project_totals(phases):
    """Sum budget/tracked hours over started, budgeted phases (so unstarted future
    budget doesn't dwarf the progress bar), plus the grand totals."""
    active = _active(phases)
    return {
        "begroot_uren_aangesneden": round(sum(p["budget_hours"] for p in active), 1),
        "gepresteerd_uren": round(sum(p["tracked_hours"] for p in active), 1),
        "begroot_uren_totaal": round(sum(p["budget_hours"] for p in phases), 1),
    }


def months_between(ym_a, ym_b):
    """Whole months from 'YYYY-MM' a to b (b later -> positive). None on junk."""
    try:
        ya, ma = int(ym_a[:4]), int(ym_a[5:7])
        yb, mb = int(ym_b[:4]), int(ym_b[5:7])
    except (TypeError, ValueError, IndexError):
        return None
    return (yb - ya) * 12 + (mb - ma)


def afgerond_from_activity(last_active_ym, now_ym, months_idle):
    """Is a project finished, judged only on when time was last booked on it?

    AWP never closes projects in Teamleader -- all 187 are `status: open`, and
    `filter.status = ["closed"]` returns nothing -- so "afgerond" cannot come
    from Teamleader. The workable proxy is inactivity: nobody has booked an hour
    on it for `months_idle` months.

    A project with NO activity at all is NOT finished: it has never started.
    """
    if not last_active_ym:
        return False
    gap = months_between(last_active_ym, now_ym)
    return gap is not None and gap >= months_idle


def margin(basis_eur, kost_eur):
    """Marge = basis − effectieve kost, met pct t.o.v. de basis.
    Basis = gefactureerd (feedback ronde 2); voorheen de offerte."""
    basis = float(basis_eur or 0)
    kost = float(kost_eur or 0)
    marge = round(basis - kost, 2)
    marge_pct = round(marge / basis * 100) if basis else 0
    return marge, marge_pct
