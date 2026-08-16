"""SQLite storage on the Railway /data volume. Single-writer (gunicorn --workers 1
+ one sync thread); WAL mode + per-call connections keep it safe."""
import json
import os
import sqlite3
import time

from . import config, phases

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, naam TEXT,
  password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1, lang TEXT NOT NULL DEFAULT 'nl',
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cost_rates (
  id INTEGER PRIMARY KEY, tl_user_id TEXT NOT NULL, tl_user_naam TEXT,
  eur_per_hour REAL NOT NULL, effective_from TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_costrates ON cost_rates(tl_user_id, effective_from);
CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS project_snapshot (
  project_id TEXT PRIMARY KEY, project_key TEXT, titel TEXT, naam TEXT, adres TEXT,
  status TEXT, is_architectuur INTEGER NOT NULL DEFAULT 1, categorie TEXT, contracttype TEXT,
  verantw_arch TEXT, verantw_medewerker TEXT, budget_klant REAL, offerte_awp REAL, raming_vo REAL,
  uren_begroot REAL, uren_gepresteerd REAL, effectieve_kost REAL, gefactureerd REAL,
  uren_begroot_gestart REAL, uren_gepresteerd_gestart REAL, gefactureerd_manueel REAL,
  afgerond_manueel INTEGER,
  marge REAL, marge_pct REAL, project_type TEXT, activity_json TEXT,
  uren_per_persoon_json TEXT, kost_bron TEXT,
  summary_status TEXT, n_over INTEGER, n_warn INTEGER, cost_estimated INTEGER NOT NULL DEFAULT 0,
  werfbezoeken INTEGER, besprekingen INTEGER, attention_note TEXT, phases_json TEXT, synced_at TEXT);
CREATE TABLE IF NOT EXISTS meldingen (
  id INTEGER PRIMARY KEY, project_id TEXT NOT NULL, project_key TEXT, naam TEXT,
  phase_naam TEXT, severity TEXT NOT NULL, pct REAL, message TEXT, created_at TEXT NOT NULL,
  seen INTEGER NOT NULL DEFAULT 0, verantw TEXT, notified_at TEXT,
  soort TEXT, afgehandeld_at TEXT, afgehandeld_door TEXT,
  UNIQUE(project_id, phase_naam, severity));
CREATE TABLE IF NOT EXISTS sync_state (
  id INTEGER PRIMARY KEY CHECK(id=1), last_run_at TEXT, last_ok_at TEXT,
  running INTEGER NOT NULL DEFAULT 0, last_error TEXT, projects_synced INTEGER DEFAULT 0);
"""


def _conn():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# Columns added after the first production deploy. CREATE TABLE IF NOT EXISTS
# won't touch an existing table, so add them idempotently on every boot.
# Keyed by table: the /data volume outlives every deploy, so ANY table can need
# a column added later -- not just project_snapshot.
# Never remove an entry here: a volume restored from an old backup still needs it.
_MIGRATE_COLS = {
    "project_snapshot": (
        ("gefactureerd", "REAL"),
        ("project_type", "TEXT"),
        ("activity_json", "TEXT"),
        ("uren_per_persoon_json", "TEXT"),
        ("kost_bron", "TEXT"),
        ("uren_begroot_gestart", "REAL"),
        ("uren_gepresteerd_gestart", "REAL"),
        ("gefactureerd_manueel", "REAL"),
        ("afgerond_manueel", "INTEGER"),
    ),
    "meldingen": (
        ("verantw", "TEXT"),
        ("notified_at", "TEXT"),
        ("soort", "TEXT"),
        ("afgehandeld_at", "TEXT"),
        ("afgehandeld_door", "TEXT"),
    ),
}


def init_db():
    with _conn() as c:
        c.executescript(_SCHEMA)
        c.execute("INSERT OR IGNORE INTO sync_state(id, running) VALUES (1, 0)")
        # A fresh process cannot have a sync in flight. run_full() clears
        # `running` only in its finally block, so a deploy or a crash mid-sync
        # leaves it stuck at 1 -- and every later run_full() returns immediately,
        # silently freezing the cache for good. Seen in production: the flag sat
        # at 1 for hours across several deploys, and nothing synced any more.
        # Safe because the Procfile pins gunicorn to a single worker.
        c.execute("UPDATE sync_state SET running=0 WHERE id=1")
        for table, cols in _MIGRATE_COLS.items():
            existing = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            if not existing:
                continue          # table not created yet -> _SCHEMA already has it
            for col, typ in cols:
                if col not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    _seed_default_config()


# ---------- config ----------
def get_config(key, default=None):
    with _conn() as c:
        row = c.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_config(key, value):
    with _conn() as c:
        c.execute("INSERT INTO config(key,value) VALUES(?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, json.dumps(value)))


def _seed_default_config():
    defaults = {
        "thresholds": config.DEFAULT_THRESHOLDS,
        "internal_cost_rate": config.DEFAULT_INTERNAL_COST_RATE,
        "external_rate": config.DEFAULT_EXTERNAL_RATE,
        "front_office_rate": config.DEFAULT_FRONT_OFFICE_RATE,
        "sync_interval_minutes": config.DEFAULT_SYNC_INTERVAL_MINUTES,
        "custom_field_ids": {},
        "worktype_ids": {},
        "phase_taxonomy": phases.DEFAULT_TAXONOMY,
        "status_basis": config.DEFAULT_STATUS_BASIS,
        "project_thresholds": config.DEFAULT_PROJECT_THRESHOLDS,
    }
    for k, v in defaults.items():
        if get_config(k, None) is None:
            set_config(k, v)


# ---------- users ----------
def create_user(email, naam, password_hash, is_admin=0, lang="nl"):
    with _conn() as c:
        c.execute("INSERT INTO users(email,naam,password_hash,is_admin,active,lang,created_at)"
                  " VALUES(?,?,?,?,1,?,?)",
                  (email.lower().strip(), naam, password_hash, int(is_admin), lang, now_iso()))


def get_user_by_email(email):
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE email=? AND active=1",
                      (email.lower().strip(),)).fetchone()
    return dict(r) if r else None


def get_user(uid):
    with _conn() as c:
        r = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return dict(r) if r else None


def list_users():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM users ORDER BY naam").fetchall()]


def count_users():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]


def set_user_lang(uid, lang):
    with _conn() as c:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))


# ---------- cost rates ----------
def add_cost_rate(tl_user_id, naam, eur_per_hour, effective_from):
    with _conn() as c:
        c.execute("INSERT INTO cost_rates(tl_user_id,tl_user_naam,eur_per_hour,effective_from,created_at)"
                  " VALUES(?,?,?,?,?)", (tl_user_id, naam, float(eur_per_hour), effective_from, now_iso()))


def list_cost_rates():
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM cost_rates ORDER BY tl_user_naam, effective_from DESC").fetchall()]


def cost_rate_map():
    """{tl_user_id: [(effective_from, eur_per_hour), ...] desc} for date lookup.

    sync._rate_for() walks each list top-down and takes the first row whose
    effective_from <= the entry date, so the per-user list MUST be sorted by
    effective_from descending. list_cost_rates() orders by name first (display
    order), which breaks that when a user's name changed between rows -- so we
    re-sort here. Ties on the same date: the most recently inserted row (highest
    id) wins, so a same-day correction supersedes the original.
    """
    out = {}
    for r in list_cost_rates():
        out.setdefault(r["tl_user_id"], []).append(
            (r["effective_from"], r["eur_per_hour"], r["id"]))
    return {uid: [(eff, rate) for eff, rate, _ in
                  sorted(rows, key=lambda x: (x[0], x[2]), reverse=True)]
            for uid, rows in out.items()}


def has_cost_rates():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM cost_rates").fetchone()["n"] > 0


# ---------- snapshots ----------
def upsert_snapshot(s):
    cols = ["project_id", "project_key", "titel", "naam", "adres", "status", "is_architectuur",
            "categorie", "contracttype", "verantw_arch", "verantw_medewerker", "budget_klant",
            "offerte_awp", "raming_vo", "uren_begroot", "uren_gepresteerd", "effectieve_kost",
            "uren_begroot_gestart", "uren_gepresteerd_gestart",
            "gefactureerd", "project_type", "activity_json",
            "uren_per_persoon_json", "kost_bron",
            "marge", "marge_pct", "summary_status", "n_over", "n_warn", "cost_estimated",
            "werfbezoeken", "besprekingen", "attention_note", "phases_json", "synced_at"]
    vals = [s.get(c) for c in cols]
    ph = ",".join("?" * len(cols))
    upd = ",".join(f"{c}=excluded.{c}" for c in cols if c != "project_id")
    with _conn() as c:
        c.execute(f"INSERT INTO project_snapshot({','.join(cols)}) VALUES({ph}) "
                  f"ON CONFLICT(project_id) DO UPDATE SET {upd}", vals)


def set_manual_invoiced(project_id, amount):
    """Invoices sent OUTSIDE Teamleader, typed in by an admin.

    Deliberately absent from upsert_snapshot's column whitelist: that whitelist
    is what the sync writes, and the sync would blank this on every run. This is
    user data, so it gets its own writer and survives every sync.
    """
    with _conn() as c:
        c.execute("UPDATE project_snapshot SET gefactureerd_manueel=? WHERE project_id=?",
                  (None if amount is None else float(amount), project_id))


def set_afgerond_manueel(project_id, value):
    """Force a project's finished/running state. NULL = follow the automatic rule.

    Same reasoning as set_manual_invoiced: user data, so it stays out of the
    sync's column whitelist and survives every run.
    """
    with _conn() as c:
        c.execute("UPDATE project_snapshot SET afgerond_manueel=? WHERE project_id=?",
                  (None if value is None else int(value), project_id))


def delete_snapshots_except(project_ids):
    with _conn() as c:
        if project_ids:
            q = ",".join("?" * len(project_ids))
            c.execute(f"DELETE FROM project_snapshot WHERE project_id NOT IN ({q})", list(project_ids))
        else:
            c.execute("DELETE FROM project_snapshot")


def list_snapshots(architectuur_only=True):
    q = "SELECT * FROM project_snapshot"
    if architectuur_only:
        q += " WHERE is_architectuur=1"
    q += " ORDER BY project_key"
    with _conn() as c:
        return [dict(r) for r in c.execute(q).fetchall()]


def get_snapshot(project_id):
    with _conn() as c:
        r = c.execute("SELECT * FROM project_snapshot WHERE project_id=?", (project_id,)).fetchone()
    return dict(r) if r else None


# ---------- meldingen ----------
def upsert_melding(project_id, project_key, naam, phase_naam, severity, pct,
                   verantw=None, soort="fase"):
    """Insert an alert, or refresh an existing one WITHOUT resetting its state.

    created_at, seen, notified_at and afgehandeld_at are deliberately left alone
    on conflict: they are what makes "this alert is not new", "we already
    emailed about it" and "someone has handled it" knowable. Without that, an
    alert ticked off would come straight back on the next hourly sync.

    One row per THRESHOLD crossed, not per current colour zone: a phase at 120%
    has crossed 80, 100 and 115, so it carries three alerts — "per fase worden
    maximaal drie meldingen gegenereerd, elk exact één keer".
    """
    with _conn() as c:
        c.execute(
            "INSERT INTO meldingen(project_id,project_key,naam,phase_naam,severity,pct,created_at,seen,verantw,soort)"
            " VALUES(?,?,?,?,?,?,?,0,?,?)"
            " ON CONFLICT(project_id,phase_naam,severity) DO UPDATE SET"
            " pct=excluded.pct, project_key=excluded.project_key,"
            " naam=excluded.naam, verantw=excluded.verantw, soort=excluded.soort",
            (project_id, project_key, naam, phase_naam, severity, pct, now_iso(),
             verantw, soort))


def prune_meldingen(project_id, keep):
    """Drop a project's alerts that no longer apply. `keep` = {(phase, severity)}.

    Replaces the old clear-everything-then-reinsert: rows that still apply are
    left untouched, so their created_at / seen / notified_at survive.
    """
    with _conn() as c:
        rows = c.execute("SELECT id, phase_naam, severity FROM meldingen WHERE project_id=?",
                         (project_id,)).fetchall()
        gone = [r["id"] for r in rows if (r["phase_naam"], r["severity"]) not in keep]
        if gone:
            q = ",".join("?" * len(gone))
            c.execute(f"DELETE FROM meldingen WHERE id IN ({q})", gone)


# ---------- alert notifications ----------
def meldingen_to_notify():
    """Alerts never emailed. Each one goes out exactly once, ever.

    The old 24h window existed because alerts were deleted and recreated on
    every sync. They persist now, so "once, full stop" is both simpler and what
    the client asked for: "één melding en één mail per fase per project".
    """
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM meldingen WHERE notified_at IS NULL"
            " ORDER BY project_key, (soort='project') DESC, pct DESC").fetchall()]


def mark_notified(ids, when=None):
    if not ids:
        return
    with _conn() as c:
        q = ",".join("?" * len(ids))
        c.execute(f"UPDATE meldingen SET notified_at=? WHERE id IN ({q})",
                  [when or now_iso()] + list(ids))


_MELDING_ORDER = (" ORDER BY (soort='project') DESC, (severity='darkred') DESC,"
                  " (severity='red') DESC, pct DESC, created_at DESC")


def list_meldingen(verantw=None, open_only=True):
    """Alerts, newest and worst first.

    `verantw` limits to one or more owner codes (the "my alerts" view);
    `open_only` hides the ones already ticked off.
    """
    where, args = [], []
    if open_only:
        where.append("afgehandeld_at IS NULL")
    if verantw:
        codes = [verantw] if isinstance(verantw, str) else list(verantw)
        if not codes:
            return []
        where.append(f"LOWER(TRIM(COALESCE(verantw,''))) IN ({','.join('?' * len(codes))})")
        args += [c.strip().lower() for c in codes]
    q = "SELECT * FROM meldingen"
    if where:
        q += " WHERE " + " AND ".join(where)
    with _conn() as c:
        return [dict(r) for r in c.execute(q + _MELDING_ORDER, args).fetchall()]


def afhandelen(melding_id, door=None):
    """Tick an alert off. It stays out of the list until its threshold is
    crossed again from scratch."""
    with _conn() as c:
        c.execute("UPDATE meldingen SET afgehandeld_at=?, afgehandeld_door=? WHERE id=?",
                  (now_iso(), door, int(melding_id)))


def heropenen(melding_id):
    with _conn() as c:
        c.execute("UPDATE meldingen SET afgehandeld_at=NULL, afgehandeld_door=NULL"
                  " WHERE id=?", (int(melding_id),))


def count_open_meldingen(verantw=None):
    """Badge count: what is still OPEN, not what has not been looked at.

    Was `seen`-based, which meant the badge only told you whether anyone had
    visited the page. Now that alerts can be handled, "open" is the number that
    matters.
    """
    return len(list_meldingen(verantw=verantw, open_only=True))


def mark_meldingen_seen():
    with _conn() as c:
        c.execute("UPDATE meldingen SET seen=1 WHERE seen=0")


# ---------- sync state ----------
def get_sync_state():
    with _conn() as c:
        r = c.execute("SELECT * FROM sync_state WHERE id=1").fetchone()
    return dict(r) if r else {}


def set_sync_state(**kw):
    if not kw:
        return
    sets = ",".join(f"{k}=?" for k in kw)
    with _conn() as c:
        c.execute(f"UPDATE sync_state SET {sets} WHERE id=1", list(kw.values()))
