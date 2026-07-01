# AWP Buro — Teamleader onboarding + nacalculatie dashboard

One Flask app (hosted on Railway) that does two things:

1. **Onboarding + API proxy** — `app.py` + `onboarding/`. A guided wizard that lets a
   Teamleader account owner connect via OAuth2 (we never see their password), an
   auto-refreshing token store, and an authenticated proxy + dev dashboard for querying
   the Teamleader API.
2. **Nacalculatie dashboard** — `nacalc/`. A bilingual (NL/EN) budget-follow-up dashboard
   for AWP Buro's architecture projects, fed live from Teamleader and cached in SQLite.

Both run in the **same** Flask process. The deploy entry point is `gunicorn app:app`.

## Project layout

```
app.py             Flask app + OAuth/proxy routes (entry point: app:app)
onboarding/        Onboarding wizard + dev dashboard — HTML templates (pages.py)
nacalc/            The dashboard
  config.py        constants, rates, thresholds, custom-field mapping
  store.py         SQLite cache (projects, users, config, alerts, sync state)
  teamleader.py    Teamleader API client (read-only)
  sync.py          Teamleader → compute → cache (hourly + "Sync nu")
  calc.py          pure calculations (phase %, colors, margin) — no IO
  auth.py          per-user login (scrypt), session guards
  i18n.py          all NL/EN UI text
  views.py         Flask routes (blueprint) — the pages
  ui/
    components.py  small render helpers (money, phase dots, bars, status cell)
    pages.py       full page HTML (shell, overzicht, drawer, meldingen, analyse, beheer)
assets/css/        ⭐ ALL styling
  dashboard.css    dashboard theme
  onboarding.css   wizard/dev theme
scripts/           dev-only helpers (not run in production)
docs/              HANDOFF.md, DEPLOY.md, AUDIT.md, Nacalculatie-uitleg.pdf
```

## Where to make changes

| I want to change… | Edit |
|---|---|
| **Look & feel (colors, fonts, spacing)** | `assets/css/dashboard.css` (dashboard) or `assets/css/onboarding.css` (wizard). No Python. |
| **UI text (NL/EN)** | `nacalc/i18n.py` |
| **Page structure / markup** | `nacalc/ui/pages.py`, `onboarding/pages.py` |
| **Calculations** | `nacalc/calc.py` + `nacalc/sync.py` (see `docs/AUDIT.md`) |
| **Rates / thresholds / mappings** | `nacalc/config.py` + the in-app **Beheer** page |

👉 **Taking over this project? Start with [`docs/HANDOFF.md`](docs/HANDOFF.md)** — full
architecture + a step-by-step "change the look" playbook.

## Run locally

```bash
pip install -r requirements.txt
# run without touching Teamleader (no sync):
NACALC_DISABLE_SYNC=1 python app.py        # PowerShell: $env:NACALC_DISABLE_SYNC=1; python app.py
# open http://localhost:8765/app  (dashboard, requires login) or http://localhost:8765/ (wizard)
python scripts/smoke_test.py               # quick health check of every page
```

## Deploy

Railway, `gunicorn app:app` (see `Procfile` / `railway.json`). Full steps and the required
environment variables are in [`docs/DEPLOY.md`](docs/DEPLOY.md). Redeploy with `railway up`.
