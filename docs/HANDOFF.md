# HANDOFF — how this project works (and how to restyle it)

> Audience: a developer **or another LLM** taking over this codebase. Read §1–§3 for the
> mental model, then jump to **§5 (the CSS playbook)** — that is where 90% of look-and-feel
> changes happen, and it needs **no Python**.

---

## 1. What this is (30-second model)

One **Flask** app (Python), hosted on **Railway**, serving **two things** in the same process:

1. **Onboarding + API proxy** (`app.py` + `onboarding/`)
   A guided OAuth2 wizard so a non-technical Teamleader account owner can connect their
   account (we never see their password). Tokens are stored and auto-refreshed. A developer
   then reads the Teamleader API through an authenticated proxy (`/api/...`) or the `/dev`
   dashboard. This is the "cream/serif" looking set of pages.

2. **Nacalculatie dashboard** (`nacalc/`)
   The real product: a bilingual (NL/EN) budget-follow-up dashboard for AWP Buro's
   architecture projects. It is fed **live from Teamleader**, cached in **SQLite**, and shown
   under `/app/...`. This is the "blue SaaS" looking dashboard.

**Entry point:** `gunicorn app:app` (the variable `app` in `app.py`). Do not rename either.

---

## 2. Architecture & data flow

```
                       ┌─────────────── ONBOARDING (app.py + onboarding/) ───────────────┐
Browser  ──/ , /dev──▶ │ OAuth wizard, /connect, /oauth/callback, /token, /api/<endpoint> │
                       │ stores tokens.json, auto-refreshes → get_valid_access_token()    │
                       └────────────────────────────────────────────────────────────────┘
                                                    │ shares the token
                                                    ▼
   ┌──────────── DASHBOARD (nacalc/) ────────────────────────────────────────────────────┐
   │  Background sync (hourly + "Sync nu" button):                                        │
   │     teamleader.py  ──API──▶  sync.py  ──uses──▶  calc.py   ──writes──▶  store.py (SQLite)
   │  Page request:                                                                       │
   │     Browser ──/app──▶ views.py ──reads──▶ store.py ──renders──▶ ui/pages.py + ui/components.py
   │                                              (HTML)          (CSS inlined from assets/css/)
   └─────────────────────────────────────────────────────────────────────────────────────┘
```

Key rule: **pages never call Teamleader.** They only read the SQLite cache. The `sync.py`
engine is the only thing that talks to Teamleader; it runs on a timer and on the manual
"Sync nu" button. So the UI is always fast, and the data is at most ~1h old.

**Two-level data model (important for understanding the numbers):**
- **Per phase** = money (€): `spent € / budget €` of each Teamleader project group. Teamleader
  gives **no hours per phase**, only € — that's the central limitation.
- **Per project** = real hours (time tracking) × internal cost rate, and the AWP quote (offerte).
- This is why a project can show status "Nog niet gestart" (no € consumed in any phase) while
  still having logged hours. Full detail of every number is in [`AUDIT.md`](AUDIT.md).

---

## 3. File-by-file map

| File | What it does | Touch it to… |
|---|---|---|
| `app.py` | Flask app object + OAuth/token/proxy routes. Ends by calling `register_nacalc(app)`. | change onboarding/proxy **routes** or OAuth logic |
| `onboarding/pages.py` | HTML templates for the wizard + `/dev` (strings with `__PLACEHOLDER__`), and `render_info()`. Loads `onboarding.css`. | change wizard/dev **markup** |
| `nacalc/config.py` | Constants: rates (€65 internal / €90 external), thresholds (80/100/115), custom-field label→id map, work-type names, non-architecture types. | change **defaults** |
| `nacalc/store.py` | SQLite: schema + all reads/writes (projects snapshot, users, config, alerts, sync state). | change the **DB / queries** |
| `nacalc/teamleader.py` | Read-only Teamleader API client (`tl`, `tl_all`, typed fetchers). Uses the shared token from `app.py`. | change **which API data** is pulled |
| `nacalc/sync.py` | The sync engine: pull → `_compute()` a per-project snapshot → store → raise alerts. Background thread + manual trigger. | change **how data is computed/synced** |
| `nacalc/calc.py` | Pure functions (no IO): `color_for`, `build_phases`, `project_summary`, `margin`. Unit-testable. | change **calculation rules** |
| `nacalc/auth.py` | Per-user login (scrypt), `@login_required` / `@admin_required`, admin bootstrap. | change **auth** |
| `nacalc/i18n.py` | Every NL/EN UI string, keyed. `t(key, lang)`. | change **text / translations** |
| `nacalc/views.py` | Flask blueprint: the routes/pages (`/app`, `/app/analyse`, `/app/meldingen`, `/app/beheer`, `/app/project/<id>`, sync, login). Reads store, calls `ui.pages`. | change **routing / what data a page gets** |
| `nacalc/ui/components.py` | Small render helpers: `eur()`, phase dots (`_dot`,`dots`), `bar_color`, `_status_cell`, analysis bar `_abar`. | change a **reusable widget** |
| `nacalc/ui/pages.py` | Full page HTML: `shell` (sidebar+topbar+drawer script), `login_page`, `render_overzicht/drawer/meldingen/analyse/beheer`. Loads `dashboard.css`. | change page **markup/layout** |
| `assets/css/dashboard.css` | ⭐ All dashboard styling. | **restyle the dashboard** |
| `assets/css/onboarding.css` | ⭐ All wizard/dev styling. | **restyle the wizard** |
| `scripts/` | Dev-only, never imported by the app: `api_test.py` (API demo), `teamleader_oauth.py` + `refresh_and_call.py` (local OAuth helpers), `smoke_test.py` (health check). | run local dev helpers |

---

## 4. How the CSS is wired (read this before §5)

The CSS is **not** in the Python files anymore. Each `.css` file is read from disk **once at
import** and injected into a `<style>…</style>` block:

```python
# nacalc/ui/pages.py
STYLE = "<style>" + _load_css("dashboard.css") + "</style>"
# onboarding/pages.py
STYLE = "<style>" + _load_css("onboarding.css") + "</style>"
```

So the rendered HTML is byte-for-byte identical to before, but the CSS now lives in a real,
syntax-highlighted `.css` file. **To restyle, edit the `.css` file and redeploy** — you never
touch Python for pure aesthetics.

> Prefer serving CSS as static `<link>` files instead of inlining? It's a small change:
> set `app = Flask(__name__, static_folder="assets")`, replace each `STYLE` string with
> `'<link rel="stylesheet" href="/static/css/dashboard.css">'`, and drop the `_load_css`
> helper. Trade-off: browser-caches nicely, but adds a request and must be tested on Railway.
> The current inline approach is intentionally the zero-risk default.

---

## 5. ⭐ The "change the look" playbook (dashboard)

Everything below is in **`assets/css/dashboard.css`** unless noted.

### 5.1 Design tokens — the first place to edit

The very top of `dashboard.css` is a `:root { … }` block. Change a value here and it updates
**everywhere** that token is used.

| Token | Controls |
|---|---|
| `--bg` | page background behind the cards |
| `--panel` | card / table / KPI background (white) |
| `--ink` | main text color |
| `--muted` | secondary/label text |
| `--line` | borders and dividers |
| `--sidebar` | left navigation background (dark navy) |
| `--sidebar-ink` | left navigation text |
| `--accent` | **primary blue**: buttons, active nav item, links, project-key badge, focus rings |
| `--green` / `--green-bg` | "on track" status, positive margin, phase within budget |
| `--amber` / `--amber-bg` | "at risk" (≥80% of a phase), warning |
| `--red` / `--red-bg` | "over budget", negative margin |
| `--darkred` | "well over" (≥115%) |
| `--grey` / `--grey-bg` | neutral: not-started, empty bars, tags |
| `--shadow` | card elevation |

Fonts: the dashboard uses the system UI font stack (set on `body`). To change it, edit the
`font-family` on the `body{…}` rule near the top.

### 5.2 Which class styles which part of the screen

| Screen area | Main CSS classes |
|---|---|
| Left sidebar | `.side`, `.brand`, `.logo`, `.nav`, `.nav a`, `.nav a.active`, `.badge`, `.side-foot` |
| Collapse/expand rail | `.rail-toggle`, `.app.collapsed …` (all the collapsed states) |
| Mobile top nav (≤1100px) | `.mobnav` |
| Top bar (title, sync pill, button) | `.top`, `.top h1`, `.pill`, `.btn` |
| Filter bar (search + dropdowns) | `.filters`, `.search`, `.filters select` |
| KPI cards (the 4 numbers) | `.kpis`, `.kpi`, `.kpi .lab`, `.kpi .val`, `.up`, `.ok` |
| Projects table | `.card`, `.tablewrap`, `table`, `thead th`, `tbody td`, `tbody tr`, `.sortable` |
| Project cell (key + name) | `.pcell`, `.pkey`, `.pname`, `.psub` |
| Owner / tags / numbers | `.who`, `.tag`, `.num` |
| Hours mini progress bar | `.bar`, `.bar>i`, `.barlab` |
| Phase dots + legend | `.phases`, `.pdot`, `.c-good/.c-warn/.c-over/.c-crit/.c-todo/.c-none`, `.st-done`, `.st-progress`, `.legend-ph` |
| Status cell + row accent | `.st-cell`, `.st-ic`, `.st-tx`, `tr.row-over/.row-warn/.row-ok` |
| Margin chip | `.marge-chip`, `.marge-chip.pos`, `.marge-chip.neg` |
| Empty / loading state | `.state`, `.state .sp` (spinner) |
| Rates banner | `.rbanner` |
| **Detail popup (drawer)** | `.scrim`, `.drawer`, `.dr-head`, `.dr-body`, `.meta-grid`, `.mc`, `.sec-t`, `.fase-row`, `.fbar`, `.fr-meta`, `.note` |
| **Meldingen (alerts)** | `.alert`, `.ai`, `.ai-warn/.ai-over`, `.at`, `.ad`, `.ax .pct` |
| **Analyse (the 4 graphs)** | `.grid2`, `.panel-t`, `.panel-s`, `.pinfo` (the ⓘ), `.arow`, `.an`, `.abar`, `.abar>i`, `.av` |
| Login page | `.login-wrap`, `.login`, `.login input`, `.login button`, `.login .err` |
| Beheer (settings) | `.be-card`, `.be-row`, `.savemsg` |
| Responsive breakpoint | `@media(max-width:1100px)` — hides sidebar, shows `.mobnav`, KPIs → 2 cols, `.grid2` → 1 col |

### 5.3 The 4 analysis graphs (they matter to the client)

All four are horizontal **bars** built from the same markup: `.arow` (a row) → `.an` (the
label) → `.abar > i` (the coloured fill) → `.av` (the value). To restyle the graphs' shape/
height/label, edit `.arow`, `.abar`, `.abar>i`, `.av` in `dashboard.css`.

The **bar colours and fill widths** are decided in Python, in
`nacalc/ui/pages.py → render_analyse()` — each graph has a short rule like
`color = "var(--red)" if pct >= 100 else "var(--amber)" if pct >= 80 else "var(--green)"`.
Those `var(--red/amber/green)` still resolve to the tokens above, so:
- To change *what red/amber/green look like* → edit the tokens (CSS only).
- To change *the % cut-offs* that pick a colour on a graph → edit `render_analyse()` (Python).

The bar tooltips (hover text) and titles are in `nacalc/i18n.py` (`an_tip_*`, `an_info_*`).

### 5.4 ⚠️ Colours that come from Python, not CSS

Status/phase colours are *chosen* in Python and *rendered* via the tokens. Know the split:
- `nacalc/calc.py → color_for()` maps a consumption % to `green/amber/red/darkred/none`.
- `nacalc/ui/components.py → bar_color()` maps those names to `var(--green)` etc; `_dot()` maps
  them to the `.c-good/.c-warn/.c-over/.c-crit` classes.

So: **appearance of a status colour = CSS token**; **the threshold at which it flips** =
`nacalc/config.py DEFAULT_THRESHOLDS` (or the in-app **Beheer** page). Don't hunt in CSS for
"why is this phase amber" — that's a threshold, not a style.

### 5.5 Gotcha: CSS unicode escapes

`onboarding.css` contains `content:"\2713"` (a ✓) and `content:"\203A"` (a ›). Keep the
**single** backslash. (In the old Python source these were written `\\2713`; the extraction
already converted them correctly — just don't re-double them.)

### 5.6 Onboarding / dev theme

The wizard + `/dev` pages use a completely separate theme in **`assets/css/onboarding.css`**
(warm "paper" palette, Fraunces serif display font). Its tokens: `--paper`, `--card`, `--ink`,
`--accent` (a green), `--font-display` (Fraunces), `--font-body` (Hanken Grotesk),
`--font-mono` (JetBrains Mono), `--radius`. Editing this file does **not** affect the dashboard,
and vice-versa.

### 5.7 The change → verify → deploy loop

```bash
# 1. edit assets/css/dashboard.css (or onboarding.css)
# 2. verify nothing broke:
python scripts/smoke_test.py
# 3. eyeball it locally:
NACALC_DISABLE_SYNC=1 python app.py     # http://localhost:8765/app  (login) / 8765/ (wizard)
# 4. ship it:
railway up
```

---

## 6. Text & translations

All UI text is in `nacalc/i18n.py` as `S = { "key": {"nl": "...", "en": "..."} }`, read via
`t("key", lang)`. Some strings use `.format(...)` placeholders (the analysis tooltips). To add
a label: add a key to `S`, then reference `t("your_key", lang)` in `nacalc/ui/pages.py`.
Teamleader **data** (project names, phase names, categories) is never translated.

---

## 7. Data & calculations

For the exact formula behind every number, chart and drawer field, see [`AUDIT.md`](AUDIT.md)
(it cross-references `sync.py`, `calc.py`, `views.py`, `ui/pages.py`). The short version:

- **Phase %** = `spent € / budget €` per Teamleader project group → colour via thresholds.
- **Project hours** = Σ time-tracking entries; **cost** = hours × €65 (internal rate).
- **Margin** = AWP quote − cost (blank "—" when there's no quote).
- **Status** = strictest colour across started, budgeted phases.

Rates, thresholds and the custom-field mapping live in `nacalc/config.py` and can be overridden
at runtime on the in-app **Beheer** page (stored in the `config` table).

---

## 8. Run locally & deploy

**Local:**
```bash
pip install -r requirements.txt
NACALC_DISABLE_SYNC=1 python app.py     # no Teamleader calls; empty dashboard renders fine
python scripts/smoke_test.py            # asserts every page returns 200 with CSS
```
To exercise real data locally you'd need Teamleader OAuth env vars and a connected account —
not needed for UI/CSS work.

**Deploy (Railway):** `railway up`. Full first-time setup + all environment variables are in
[`DEPLOY.md`](DEPLOY.md). Required env vars: `TL_CLIENT_ID`, `TL_CLIENT_SECRET`, `DEV_API_KEY`,
`SECRET_KEY`, `DATA_DIR=/data` (+ a mounted `/data` volume), optional `BOOTSTRAP_ADMIN_EMAIL` /
`BOOTSTRAP_ADMIN_PASSWORD`, `APP_HOST`, `SYNC_INTERVAL_MINUTES`, `NACALC_DISABLE_SYNC`.

---

## 9. Guardrails — do not break these

- **Entry point stays `gunicorn app:app`** and `--workers 1` (multiple workers race the token
  file during refresh-token rotation).
- **Mount the `/data` volume** so `tokens.json` + `nacalc.db` survive redeploys.
- **Teamleader access is read-only** — only `.list` / `.info` calls. Never write to the client's
  account.
- **Secrets never committed**: `tokens.json`, `*.db`, `.env` are git-ignored. Rotate `DEV_API_KEY`
  if it leaks; the Teamleader `CLIENT_ID/SECRET` circulated in plaintext and should be rotated.
- **Don't change the DB schema** (`store.py _SCHEMA`) without a migration — the `/data` volume
  persists old rows.
- Keep the CSS files byte-clean (see §5.5). If you split or rename `ui/pages.py` /
  `onboarding/pages.py`, keep the `_load_css` path pointing at `assets/css/`.

---

## 10. Common tasks cookbook

| Task | Do this |
|---|---|
| Change the primary blue | `dashboard.css` → `--accent` |
| Make "over budget" a different red | `dashboard.css` → `--red` / `--red-bg` |
| Restyle the KPI cards | `dashboard.css` → `.kpi`, `.kpi .val` |
| Change the detail popup width | `dashboard.css` → `.drawer { width: … }` |
| Change graph bar height | `dashboard.css` → `.abar`, `.arow` |
| Change *when* a phase turns amber/red | `nacalc/config.py DEFAULT_THRESHOLDS` or the Beheer page |
| Rename a label / add a translation | `nacalc/i18n.py` |
| Add a sidebar nav item | `nacalc/ui/pages.py` → `shell()` `navitem(...)`, add a `views.py` route |
| Add a KPI card | `nacalc/views.py overzicht()` `kpis=[…]` + style via `.kpi` |
| Change the internal cost rate | Beheer page, or `nacalc/config.py DEFAULT_INTERNAL_COST_RATE` |
| Restyle the wizard | `assets/css/onboarding.css` |
