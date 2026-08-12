"""Config & constants for the AWP Buro nacalculatie dashboard."""
import os

DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "nacalc.db")

# Teamleader API base (calls go directly server-side via the shared token helpers).
API_BASE = "https://api.focus.teamleader.eu"

# Default thresholds (% of a phase's budget consumed) -> color. Configurable in /beheer.
DEFAULT_THRESHOLDS = {"amber": 80, "red": 100, "darkred": 115}

# Fixed rates (AWP Buro, per Teamleader): internal cost €65/h, external billing €90/h.
# Margin = offerte (AWP quote) − (tracked hours × internal cost rate). Editable in Beheer.
DEFAULT_INTERNAL_COST_RATE = 65.0
DEFAULT_EXTERNAL_RATE = 90.0
DEFAULT_FRONT_OFFICE_RATE = 90.0  # legacy alias (kept for compatibility)

# Sync cadence
DEFAULT_SYNC_INTERVAL_MINUTES = int(os.environ.get("SYNC_INTERVAL_MINUTES", "60"))

# Shape of the data written into project_snapshot. Bump this whenever _compute
# starts producing new/changed fields: on boot, a cache written by an older
# version is refreshed once (see sync._loop), so the UI never shows stale rows
# under new labels. Only bumped after a SUCCESSFUL full sync.
# 4: phases carry their canonical identity (canon/canon_label/canon_order/
#    overhead) so the analysis groups and the rollup skips overhead.
CURRENT_DATA_VERSION = 4

# Project custom-field labels we map to ids on first sync (Teamleader 'project' context).
CF_LABELS = {
    "architectuur": "Architectuur",
    "type": "2. Type",
    "categorie": "3. Categorie",
    "contracttype": "Contracttype",
    "budget_bh": "Budget BH",
    "raming_awp": "Raming AWP",
    "werfadres": "4. Werfadres",
    "verantw": "1. Verantw.",
}

# Work-type names used for the werfbezoek / bespreking counters.
WORKTYPE_WERFBEZOEK = "Werfbezoek"
WORKTYPE_BESPREKING = "Bespreking klant"

# Project 'type' custom-field values that are NOT architecture (excluded in Fase 1).
NON_ARCHITECTUUR_TYPES = {"stedenbouw", "epb", "epc", "epc/epb", "wegenis"}

BOOTSTRAP_ADMIN_EMAIL = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "")
BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
