"""Teamleader data layer. Calls the API directly server-side using the shared,
auto-refreshing token from app.py (lazy import avoids a circular import)."""
import time

import requests

from . import config


def _token():
    from app import get_valid_access_token  # lazy: app imports nacalc at the bottom
    return get_valid_access_token()


def tl(endpoint, body=None, retries=2):
    token = _token()
    if not token:
        raise RuntimeError("not_connected")
    url = f"{config.API_BASE}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    last = None
    for _ in range(retries + 1):
        r = requests.post(url, headers=headers, json=body or {}, timeout=30)
        last = r
        if r.status_code == 429:
            time.sleep(5)
            continue
        r.raise_for_status()
        return r.json()
    last.raise_for_status()


def tl_all(endpoint, body=None, size=20, maxpages=100):
    """Paginate-until-empty with a repeat-guard (some nextgen list endpoints
    ignore page.number and re-serve the first page)."""
    out, seen, n = [], set(), 1
    base = dict(body or {})
    while n <= maxpages:
        b = dict(base)
        b["page"] = {"size": size, "number": n}
        data = tl(endpoint, b).get("data")
        if not isinstance(data, list) or not data:
            break
        ids = tuple(x.get("id") for x in data)
        if ids and ids[0] in seen:
            break
        seen.update(ids)
        out += data
        if len(data) < size:
            break
        n += 1
    return out


# ---------- typed fetchers ----------
def list_project_ids():
    return [p["id"] for p in tl_all("projects-v2/projects.list", {}, size=20)]


def project_info(pid):
    return tl("projects-v2/projects.info", {"id": pid}).get("data", {})


def project_groups(pid):
    return tl_all("projects-v2/projectGroups.list", {"filter": {"project_id": pid}}, size=20)


def project_time_entries(pid):
    return tl_all("timeTracking.list",
                  {"filter": {"relates_to": {"type": "nextgenProject", "id": pid}}}, size=20)


def quotation_info(qid):
    return tl("quotations.info", {"id": qid}).get("data", {})


def list_users():
    return tl_all("users.list", {}, size=50)


def list_work_types():
    return tl("workTypes.list", {"page": {"size": 100}}).get("data", [])


def list_custom_field_defs():
    return tl("customFieldDefinitions.list", {"page": {"size": 100}}).get("data", [])


# ---------- helpers ----------
def cf_value(custom_fields, cf_id):
    """Read a custom-field value by definition id (handles both shapes)."""
    if not cf_id:
        return None
    for item in custom_fields or []:
        iid = item.get("id") or (item.get("definition") or {}).get("id")
        if iid == cf_id:
            return item.get("value")
    return None


def amount(money):
    return float((money or {}).get("amount") or 0) if isinstance(money, dict) else 0.0


def hours(timeobj):
    return round(float((timeobj or {}).get("value") or 0) / 3600, 2) if isinstance(timeobj, dict) else 0.0
