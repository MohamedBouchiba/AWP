# Deploying the Teamleader onboarding app on Railway

Goal: host a small web app so the **non-technical owner** connects their Teamleader
account through a guided wizard, and **you (the developer)** end up with working API
access — without ever handling OAuth yourself.

- Owner page (English wizard): `https://<your-app>.up.railway.app/`
- Developer dashboard: `https://<your-app>.up.railway.app/dev?key=<DEV_API_KEY>`

---

## The order matters (chicken-and-egg)

The redirect URI to whitelist is `https://<domain>/oauth/callback`, but the domain only
exists once Railway generates it. So the sequence is:

**deploy → volume → domain → env vars → verify on /dev → whitelist in Teamleader → owner connects.**

The wizard always displays the exact redirect URI to whitelist (read from the server), so
once the domain exists everything lines up automatically.

---

## 1. Install the Railway CLI (no npm needed)

`npm` / `scoop` aren't required — download the prebuilt Windows binary from the
[Railway CLI releases](https://github.com/railwayapp/cli/releases) (`railway.exe`) and put
it on your PATH, then:

```powershell
railway --version
```

(Alternatively, if you have Node: `npm i -g @railway/cli`; or Scoop: `scoop install railway`.)

## 2. Log in (one-time, opens your browser)

```powershell
railway login
```

Creates a free Railway account if you don't have one.

## 3. Create the project and deploy

From the project folder:

```powershell
railway init        # name it e.g. "teamleader-onboarding"
railway up          # uploads this folder; Railpack auto-detects Python (requirements.txt + Procfile)
```

The first boot has no domain and no tokens yet — that's expected.

## 4. Add a persistent volume (DASHBOARD — do this before the owner connects)

Without a volume, Railway's filesystem is wiped on every redeploy and the owner's tokens
would be lost.

- Railway dashboard → your service → **Settings → Volumes → New Volume**
- **Mount path: `/data`**

(Newer CLI may support `railway volume add -m /data` — try it; otherwise use the dashboard.)

## 5. Generate the public domain

- Try the CLI: `railway domain`
- Or dashboard → service → **Settings → Networking → Generate Domain**

Copy the URL, e.g. `https://teamleader-onboarding.up.railway.app`.

## 6. Set the environment variables

```powershell
railway variables --set "TL_CLIENT_ID=<client_id>" --set "TL_CLIENT_SECRET=<client_secret>" --set "DEV_API_KEY=<random>" --set "SECRET_KEY=<random>" --set "DATA_DIR=/data"
```

Generate the two random secrets (run twice):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Notes:
- **`REDIRECT_URI` is usually unnecessary.** With a domain, Railway injects
  `RAILWAY_PUBLIC_DOMAIN` and the app derives the callback URL automatically. Only set
  `REDIRECT_URI` for a custom domain — and then it must be **exactly**
  `https://<that-domain>/oauth/callback`.
- Setting variables / attaching the volume triggers a redeploy. Make sure the final running
  deployment has **both** the volume **and** the domain. Re-run `railway up` if needed.

## 7. Verify as the developer

Open: `https://<domain>/dev?key=<DEV_API_KEY>`

- The configuration checklist should be all green.
- The redirect URI shown should be `https://<domain>/oauth/callback` with no mismatch warning.
- The owner isn't connected yet, so a test query returns **409** — that's expected.

## 8. Whitelist the redirect URI in Teamleader (admin)

Add the **exact** redirect URI (`https://<domain>/oauth/callback`) in
Marketplace → your integration → **Build** → **Redirect URIs** → save.
(This is the production URL — the second one we said we'd add.)

## 9. Send the owner the link

Send them just: `https://<domain>/`

The wizard walks them through whitelisting (already done by the admin in step 8 — they'll
see the same URL) and connecting. Watch `/dev` (or `/status`) flip to **Connected**.

## 10. Final check

On `/dev`, run **users.me** (shows the owner's identity) and **contacts.list** (real data).
Green = you have full API access.

---

## How you query the data day-to-day

Once connected, you never need the owner again. Two options:

**A) Proxy (simplest — you never touch tokens):**

```python
import requests
BASE = "https://<domain>"
HEADERS = {"X-Dev-Key": "<DEV_API_KEY>"}

r = requests.post(f"{BASE}/api/contacts.list", headers=HEADERS, json={"page": {"size": 20}})
print(r.json())
```

**B) Get a raw access token:**

```powershell
curl https://<domain>/token -H "X-Dev-Key: <DEV_API_KEY>"
```

Useful Teamleader endpoints (via `/api/...`): `users.me`, `contacts.list`, `companies.list`,
`deals.list`, `invoices.list`, `projects.list`. Full docs: https://developer.teamleader.eu/

---

## Routes

| Route | Who | Purpose |
|---|---|---|
| `GET /` | Owner | Guided 3-step onboarding wizard |
| `GET /connect` | Owner | Starts the OAuth flow |
| `GET /oauth/callback` | Teamleader | Stores tokens, returns to `/` |
| `GET /status` | Public | `{"connected": bool, ...}` (drives the live status pill) |
| `GET /verify` | Public | Runs a live `users.me` query and returns `{"ok": bool, "name": …}` — the end-to-end proof the wizard shows the owner on the final step (cached ~30s) |
| `GET /dev?key=…` | Dev | Verification dashboard + test queries (auto-runs `users.me` on load) |
| `GET /token` | Dev | Fresh access token (header `X-Dev-Key`) |
| `GET\|POST /api/<endpoint>` | Dev | Authenticated proxy to Teamleader |
| `GET /healthz` | — | Liveness probe |

## Operational notes / gotchas

- **Keep `--workers 1`** (Procfile + railway.json). Multiple workers can race the token file
  during Teamleader's refresh-token rotation and log the owner out.
- **Mount the `/data` volume before the owner connects**, or the first redeploy wipes the tokens.
- **Set a stable `SECRET_KEY`** env var — the random fallback regenerates on each restart and
  breaks in-flight OAuth sessions. `/dev` flags this if it's missing.
- Secrets (`tokens.json`, `DEV_API_KEY`) are never committed (see `.gitignore`). Rotate
  `DEV_API_KEY` in Railway variables if it leaks.
- The Teamleader `CLIENT_ID`/`CLIENT_SECRET` you tested earlier circulated in plaintext —
  consider regenerating them in Teamleader and using the fresh values here.
