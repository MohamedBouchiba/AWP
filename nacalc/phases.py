"""Phase taxonomy: canonical name, chronological order, overhead flag.

Pure functions (no IO) so they are unit-testable like calc.py. The runtime
configuration lives in the `config` table under the key `phase_taxonomy` and is
passed in as a plain dict — this module never touches the store.

Why it exists (client feedback, 2026-08):
  * "Schetsontwerp/haalbaarheid is eigenlijk hetzelfde als schetsontwerp" and
    "Aanbestedingsdossier is hetzelfde als aanbesteding" -> ALIASES, so legacy
    quote wording collapses into one phase without editing Teamleader.
  * "Het onderdeel administratie moet niet mee opgenomen worden in de toggle
    dreigt over te gaan" -> OVERHEAD, excluded from the budget-status rollup
    (still displayed, still counted in the totals).
  * "Kunnen de fases bij de analyse chronologisch staan ipv per %" -> ORDER,
    taken from the office's own quote layout rather than from a percentage.

The same three answers all come from one lookup, so the dashboard, the alerts
and the analysis can never disagree about what a phase is.
"""
import re

# Aliases are keyed and valued by NORMALISED name (see normalize()).
DEFAULT_ALIASES = {
    "schetsontwerp/haalbaarheid": "schetsontwerp",
    "schetsontwerp / haalbaarheid": "schetsontwerp",
    "haalbaarheid/schetsontwerp": "schetsontwerp",
    "aanbestedingsdossier": "aanbesteding",
}

# Phases that are overhead: barely booked on, so a tiny budget makes them jump
# over 100% and drag the whole project to "dreigt over" / "over budget".
DEFAULT_OVERHEAD = ["administratie"]

# The office's quote layout — the chronological reference for the analysis.
DEFAULT_ORDER = [
    "administratie",
    "schetsontwerp",
    "voorontwerp",
    "bouwaanvraag",
    "aanbesteding",
    "uitvoeringsdossier",
    "complete werfopvolging",
    "werfopvolging",
    "bouwcoordinatie",
    "nazorg",
    "meerwerken",
]

DEFAULT_TAXONOMY = {
    "aliases": DEFAULT_ALIASES,
    "overhead": DEFAULT_OVERHEAD,
    "order": DEFAULT_ORDER,
    "labels": {},          # canonical key -> display label override (Beheer)
}

_NUM_PREFIX = re.compile(r"^\s*\d+\s*[.)\-]?\s*")
_WS = re.compile(r"\s+")

# Phases with no configured position sort after every configured one, but still
# before the truly unknown; keeps the analysis order stable and predictable.
_ORDER_NUMBERED = 1000
_ORDER_UNKNOWN = 9999


def strip_number(naam):
    """'1. VOORONTWERP' -> 'VOORONTWERP'. Also handles '1) x' and '1 - x'.

    Supersedes views._base_of, which only matched a literal 'N.' prefix.
    """
    return _NUM_PREFIX.sub("", naam or "").strip() or (naam or "").strip()


def leading_number(naam):
    """The phase's position in ITS OWN project ('3. VOORONTWERP' -> 3), or None."""
    m = re.match(r"^\s*(\d+)\s*[.)\-]?\s", (naam or "") + " ")
    return int(m.group(1)) if m else None


def normalize(naam):
    """The grouping key: number stripped, casefolded, inner whitespace collapsed.

    views._base_of was case-sensitive, so 'Voorontwerp' and 'VOORONTWERP' became
    two separate bars in the analysis. This folds them together.
    """
    return _WS.sub(" ", strip_number(naam).casefold()).strip()


def canonical(naam, taxonomy=None):
    """Resolve a raw Teamleader group title to its canonical identity.

    Returns {"key", "label", "order", "overhead"}:
      key      grouping key, alias applied (lowercase)
      label    what to display for that group
      order    chronological rank (lower = earlier in the quote)
      overhead True -> excluded from the budget-status rollup
    """
    # `None` means "caller has no opinion" -> defaults. An explicitly EMPTY dict
    # means "no aliases, no overhead, no order" and must be honoured: `or` would
    # silently fall back to the defaults and make the feature impossible to turn off.
    tx = DEFAULT_TAXONOMY if taxonomy is None else taxonomy
    key = normalize(naam)
    # One alias hop only: a chain would let a bad config loop forever.
    key = (tx.get("aliases") or {}).get(key, key)

    order_list = tx.get("order") or []
    if key in order_list:
        order = order_list.index(key)
    else:
        n = leading_number(naam)
        order = _ORDER_NUMBERED + n if n is not None else _ORDER_UNKNOWN

    label = (tx.get("labels") or {}).get(key)
    if not label:
        # Teamleader's own convention is upper case ("VOORONTWERP"), so this
        # reproduces today's analysis labels byte for byte when no alias fires.
        label = key.upper()

    return {"key": key, "label": label, "order": order,
            "overhead": key in set(tx.get("overhead") or [])}


def sort_key(naam, taxonomy=None):
    """Chronological sort key for a phase name — order first, then label."""
    c = canonical(naam, taxonomy)
    return (c["order"], c["label"])


def suggest_aliases(names, taxonomy=None):
    """Propose merges for near-duplicate phase names (the 'optimaliseer' button).

    Two patterns cover what AWP actually has in its legacy quotes:
      * a compound name whose first slash-part is itself a phase
        ('schetsontwerp/haalbaarheid' -> 'schetsontwerp')
      * a longer name that starts with a shorter one
        ('aanbestedingsdossier' -> 'aanbesteding')

    Returns {from_key: to_key} for pairs not already aliased. Suggestions only —
    nothing is applied until an admin saves them.
    """
    tx = DEFAULT_TAXONOMY if taxonomy is None else taxonomy
    known = (tx.get("aliases") or {})
    keys = sorted({normalize(n) for n in names if normalize(n)})
    out = {}
    for k in keys:
        if k in known or k in out:
            continue
        head = k.split("/")[0].strip()
        if head != k and head in keys:
            out[k] = head
            continue
        for other in keys:
            # Require a real shared stem, not just any prefix: 'nazorg' must not
            # swallow 'na', and the two must differ by a suffix only.
            if other != k and len(other) >= 6 and k.startswith(other) and len(k) > len(other):
                out[k] = other
                break
    return out


def observed_order(names, taxonomy=None):
    """Chronological order inferred from the numbers the office actually uses.

    Feeds the Beheer 'optimaliseer' button: canonical keys sorted by their most
    common leading number, so a fresh account gets a sensible order list without
    anyone typing it in.
    """
    seen = {}
    for n in names:
        c = canonical(n, taxonomy)
        num = leading_number(n)
        if num is not None:
            seen.setdefault(c["key"], []).append(num)
        else:
            seen.setdefault(c["key"], [])
    def rank(item):
        key, nums = item
        return (sorted(nums)[len(nums) // 2] if nums else _ORDER_UNKNOWN, key)
    return [k for k, _ in sorted(seen.items(), key=rank)]
