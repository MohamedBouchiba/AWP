"""SQLite storage on the Railway /data volume. Single-writer (gunicorn --workers 1
+ one sync thread); WAL mode + per-call connections keep it safe."""
import json
import os
import sqlite3
import time

from . import config

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
  marge REAL, marge_pct REAL, project_type TEXT, activity_json TEXT,
  uren_per_persoon_json TEXT, kost_bron TEXT,
  summary_status TEXT, n_over INTEGER, n_warn INTEGER, cost_estimated INTEGER NOT NULL DEFAULT 0,
  werfbezoeken INTEGER, besprekingen INTEGER, attention_note TEXT, phases_json TEXT, synced_at TEXT);
CREATE TABLE IF NOT EXISTS meldingen (
  id INTEGER PRIMARY KEY, project_id TEXT NOT NULL, project_key TEXT, naam TEXT,
  phase_naam TEXT, severity TEXT NOT NULL, pct REAL, message TEXT, created_at TEXT NOT NULL,
  seen INTEGER NOT NULL DEFAULT 0,
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
    ),
}


def init_db():
    with _conn() as c:
        c.executescript(_SCHEMA)
        c.execute("INSERT OR IGNORE INTO sync_state(id, running) VALUES (1, 0)")
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
def upsert_melding(project_id, project_key, naam, phase_naam, severity, pct, message):
    with _conn() as c:
        c.execute(
            "INSERT INTO meldingen(project_id,project_key,naam,phase_naam,severity,pct,message,created_at,seen)"
            " VALUES(?,?,?,?,?,?,?,?,0)"
            " ON CONFLICT(project_id,phase_naam,severity) DO UPDATE SET"
            " pct=excluded.pct, message=excluded.message, created_at=excluded.created_at",
            (project_id, project_key, naam, phase_naam, severity, pct, message, now_iso()))


def clear_meldingen_for(project_id):
    with _conn() as c:
        c.execute("DELETE FROM meldingen WHERE project_id=?", (project_id,))


def list_meldingen():
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM meldingen ORDER BY (severity='darkred') DESC,"
            " (severity='red') DESC, pct DESC, created_at DESC").fetchall()]


def count_unseen_meldingen():
    with _conn() as c:
        return c.execute("SELECT COUNT(*) n FROM meldingen WHERE seen=0").fetchone()["n"]


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
