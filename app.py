"""
Teamleader OAuth2 web app -- deployed on Railway.

Goal: let a NON-technical account owner connect their Teamleader account in a
few guided steps. The app stores the tokens and refreshes them automatically.
The developer then queries the API through an authenticated proxy, never
touching OAuth.

Routes:
  GET  /                  Owner onboarding wizard (3 guided steps, English)
  GET  /connect           Redirect to Teamleader authorization
  GET  /oauth/callback    Receives the code, exchanges it for tokens, stores them
  GET  /status            Public JSON: connection state
  GET  /dev               [DEV] Verification dashboard (key via ?key= or header)
  GET  /token             [DEV] Returns a fresh access_token (header X-Dev-Key)
  *    /api/<endpoint>    [DEV] Authenticated proxy to the Teamleader API
  GET  /healthz           Liveness probe

Environment variables (set these on Railway):
  TL_CLIENT_ID       Teamleader integration client_id
  TL_CLIENT_SECRET   client_secret
  DEV_API_KEY        secret YOU use for /dev, /token and /api/*
  SECRET_KEY         key to sign Flask sessions (random, but SET IT so it's stable)
  REDIRECT_URI       (optional) otherwise derived from RAILWAY_PUBLIC_DOMAIN
  DATA_DIR           (optional) token storage dir -- use /data with a Railway volume
"""

import os
import json
import time
import datetime
import secrets
from html import escape as esc

import requests
from flask import (
    Flask, request, redirect, session, jsonify, Response, abort,
)

from onboarding.pages import (  # onboarding/dev presentation (HTML + CSS)
    FONTS, STYLE, WIZARD_HTML, INFO_HTML, DEV_LOGIN_HTML, DEV_HTML, render_info,
)

# --- Config ---
CLIENT_ID = os.environ.get("TL_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TL_CLIENT_SECRET", "")
DEV_API_KEY = os.environ.get("DEV_API_KEY", "")

AUTHORIZE_URL = "https://focus.teamleader.eu/oauth2/authorize"
TOKEN_URL = "https://focus.teamleader.eu/oauth2/access_token"
API_BASE = "https://api.focus.teamleader.eu"
MARKETPLACE_URL = "https://marketplace.focus.teamleader.eu/"

# Token storage. On Railway, mount a volume and set DATA_DIR=/data so tokens
# survive restarts/redeploys.
DATA_DIR = os.environ.get("DATA_DIR", ".")
TOKENS_FILE = os.path.join(DATA_DIR, "tokens.json")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# Short-lived cache for the live /verify check, so a public endpoint can't
# hammer the Teamleader API. Reset whenever the tokens change.
_verify_cache = {"at": 0.0, "result": None}


# --- Token storage ---
def save_tokens(tokens: dict) -> None:
    tokens = dict(tokens)
    tokens["obtained_at"] = int(time.time())  # to compute expiry
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    _verify_cache["result"] = None  # force a fresh verification after any change


def load_tokens() -> dict | None:
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def redirect_uri() -> str:
    """Public callback URL. Must be whitelisted on the Teamleader side."""
    explicit = os.environ.get("REDIRECT_URI")
    if explicit:
        return explicit
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if domain:
        return f"https://{domain}/oauth/callback"
    port = os.environ.get("PORT", "8765")
    return f"http://localhost:{port}/oauth/callback"


def public_base() -> str:
    """Scheme+host the browser actually used (honours Railway's proxy headers)."""
    proto = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{proto}://{host}"


# --- OAuth logic ---
def get_valid_access_token() -> str | None:
    """Return a valid access_token, refreshing it if needed."""
    tokens = load_tokens()
    if not tokens:
        return None

    obtained_at = tokens.get("obtained_at", 0)
    expires_in = tokens.get("expires_in", 0)
    # Refresh 60s before the real expiry, as a safety margin.
    if time.time() < obtained_at + expires_in - 60:
        return tokens["access_token"]

    # Expired -> refresh
    refresh = tokens.get("refresh_token")
    if not refresh:
        return None
    resp = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }, timeout=15)
    if resp.status_code != 200:
        # refresh_token revoked/expired: the owner must re-authorize.
        return None
    new_tokens = resp.json()
    save_tokens(new_tokens)  # Teamleader rotates the refresh_token
    return new_tokens["access_token"]


def require_dev_key() -> None:
    """Protect machine routes. Key expected in the X-Dev-Key header."""
    if not DEV_API_KEY:
        abort(500, "DEV_API_KEY not configured on the server.")
    provided = request.headers.get("X-Dev-Key", "")
    if not secrets.compare_digest(provided, DEV_API_KEY):
        abort(401, "Invalid or missing dev key (X-Dev-Key header).")


def _dev_key_from_request() -> str:
    """Key from ?key= (browser) or X-Dev-Key header (machine)."""
    return request.args.get("key", "") or request.headers.get("X-Dev-Key", "")


def _check_dev_key(provided: str) -> bool:
    return bool(DEV_API_KEY) and secrets.compare_digest(provided or "", DEV_API_KEY)


# --- Owner routes ---
@app.get("/")
def home():
    # The app has its own domain(s) (APP_HOST, comma-separated); on those, the root
    # goes straight to the dashboard (which forces login). The onboarding wizard
    # stays at "/" on the onboarding domain.
    app_hosts = [h.strip() for h in os.environ.get("APP_HOST", "").split(",") if h.strip()]
    if request.host.split(":")[0] in app_hosts:
        return redirect("/app")
    connected = load_tokens() is not None
    attempted = bool(session.pop("attempted", False)) and not connected
    html = WIZARD_HTML
    html = html.replace("__FONTS__", FONTS).replace("__STYLE__", STYLE)
    html = html.replace("__REDIRECT_URI__", esc(redirect_uri()))
    html = html.replace("__MARKETPLACE_URL__", MARKETPLACE_URL)
    html = html.replace("__CLIENT_OK__", "1" if CLIENT_ID else "0")
    html = html.replace("__INITIAL_CONNECTED__", "1" if connected else "0")
    html = html.replace("__ATTEMPTED__", "1" if attempted else "0")
    return html


@app.get("/connect")
def connect():
    if not CLIENT_ID:
        return render_info(
            "Setup incomplete",
            "The server is missing its Teamleader Client ID. "
            "Please contact your developer."), 500
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    session["attempted"] = True  # to detect a connect attempt that didn't complete
    qs = requests.compat.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri(),
        "state": state,
    })
    return redirect(f"{AUTHORIZE_URL}?{qs}")


@app.get("/oauth/callback")
def oauth_callback():
    if request.args.get("state") != session.get("oauth_state"):
        return render_info(
            "Session expired",
            "We couldn't verify your session. Please start again from the "
            "beginning."), 400
    if "error" in request.args:
        return render_info(
            "Authorization cancelled",
            f"Teamleader returned: {request.args.get('error')}. "
            "You can try again."), 400
    code = request.args.get("code")
    if not code:
        return render_info(
            "Something went wrong",
            "No authorization code was received. Please try again."), 400

    resp = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri(),
    }, timeout=15)
    if resp.status_code != 200:
        return render_info(
            "Connection failed",
            "We couldn't complete the connection. Please try again, or "
            "contact your developer.",
            detail=f"{resp.status_code} {resp.text}"), 400

    save_tokens(resp.json())
    # Land back on the wizard, which now shows the success state.
    return redirect("/")


@app.get("/status")
def status():
    tokens = load_tokens()
    if not tokens:
        return jsonify({"connected": False})
    return jsonify({
        "connected": True,
        "has_refresh_token": bool(tokens.get("refresh_token")),
        "obtained_at": tokens.get("obtained_at"),
    })


@app.get("/verify")
def verify():
    """Live end-to-end proof: call the Teamleader API and confirm we can read data.

    This is THE validation the owner sees on the final step. Cached briefly so a
    public endpoint can't hammer the API.
    """
    now = time.time()
    cached = _verify_cache["result"]
    if cached is not None and now - _verify_cache["at"] < 30:
        return jsonify(cached)

    tokens = load_tokens()
    if not tokens:
        return jsonify({"ok": False, "connected": False, "error": "not_connected",
                        "message": "Not connected yet."})

    access = get_valid_access_token()
    if not access:
        res = {"ok": False, "connected": True, "error": "token_invalid",
               "message": "Connected, but the access token could not be refreshed. "
                          "Please reconnect."}
        _verify_cache.update(at=now, result=res)
        return jsonify(res)

    try:
        r = requests.post(f"{API_BASE}/users.me",
                          headers={"Authorization": f"Bearer {access}"}, timeout=15)
    except requests.RequestException as e:
        # transient -- don't cache
        return jsonify({"ok": False, "connected": True, "error": "api_unreachable",
                        "message": f"Could not reach the Teamleader API: {e}"})

    if r.status_code != 200:
        res = {"ok": False, "connected": True, "error": "api_error",
               "status": r.status_code,
               "message": f"The Teamleader API returned an error ({r.status_code})."}
        _verify_cache.update(at=now, result=res)
        return jsonify(res)

    data = (r.json() or {}).get("data", {})
    name = " ".join(p for p in [data.get("first_name", ""),
                                data.get("last_name", "")] if p).strip()
    name = name or data.get("email", "") or "your account"
    res = {"ok": True, "connected": True, "name": name,
           "email": data.get("email", ""), "checked_at": int(now)}
    _verify_cache.update(at=now, result=res)
    return jsonify(res)


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True})


# --- Dev verification dashboard ---
@app.get("/dev")
def dev_dashboard():
    key = _dev_key_from_request()
    if not _check_dev_key(key):
        page = DEV_LOGIN_HTML.replace("__FONTS__", FONTS).replace("__STYLE__", STYLE)
        note = "" if key == "" else '<p class="form__err">Invalid key.</p>'
        if not DEV_API_KEY:
            note = ('<p class="form__err">DEV_API_KEY is not set on the server '
                    '— configure it first.</p>')
        page = page.replace("__NOTE__", note)
        resp = Response(page, mimetype="text/html")
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp, (200 if key == "" else 401)

    tokens = load_tokens()
    connected = tokens is not None

    # Connection block
    if connected:
        ts = tokens.get("obtained_at")
        if ts:
            age_min = (int(time.time()) - int(ts)) // 60
            when = (f"{datetime.datetime.utcfromtimestamp(int(ts)):%Y-%m-%d %H:%M UTC}"
                    f" ({age_min} min ago)")
        else:
            when = "unknown"
        sub = (f"Refresh token: {'yes' if tokens.get('refresh_token') else 'no'}"
               f" &middot; obtained {when}")
        status_html = (
            '<div class="stat stat--ok"><div class="stat__big">Connected</div>'
            f'<div class="stat__sub">{sub}</div></div>')
    else:
        status_html = (
            '<div class="stat stat--wait"><div class="stat__big">Not connected yet</div>'
            '<div class="stat__sub">The owner hasn\'t connected their account yet.</div></div>')

    # Config checklist (booleans only -- never expose secret values)
    data_ok = os.path.isdir(DATA_DIR) and os.access(DATA_DIR, os.W_OK)
    checks = [
        ("TL_CLIENT_ID set", bool(CLIENT_ID)),
        ("TL_CLIENT_SECRET set", bool(CLIENT_SECRET)),
        ("DEV_API_KEY set", bool(DEV_API_KEY)),
        ("SECRET_KEY is stable (env var set, not random per boot)",
         bool(os.environ.get("SECRET_KEY"))),
        (f"DATA_DIR writable ({esc(DATA_DIR)})", data_ok),
        ("tokens.json present", connected),
    ]
    checks_html = "".join(
        f'<li class="check {"check--ok" if ok else "check--bad"}">'
        f'<span class="check__icon">{"&#10003;" if ok else "&#10007;"}</span>'
        f'<span>{label}</span></li>'
        for label, ok in checks
    )

    # Redirect URI mismatch diagnostic
    server_uri = redirect_uri()
    browser_uri = public_base() + "/oauth/callback"
    mismatch_html = ""
    if server_uri != browser_uri:
        mismatch_html = (
            '<div class="banner banner--warn">'
            '<strong>Redirect URI mismatch.</strong> The server sends '
            f'<code>{esc(server_uri)}</code> but this page was opened at '
            f'<code>{esc(browser_uri)}</code>. Whitelist the <em>server</em> value '
            'in Teamleader, and check REDIRECT_URI / the domain.</div>')

    html = DEV_HTML.replace("__FONTS__", FONTS).replace("__STYLE__", STYLE)
    html = html.replace("__STATUS__", status_html)
    html = html.replace("__MISMATCH__", mismatch_html)
    html = html.replace("__CHECKS__", checks_html)
    html = html.replace("__REDIRECT_URI__", esc(server_uri))
    html = html.replace("__DEV_KEY_JSON__", json.dumps(key))
    resp = Response(html, mimetype="text/html")
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


# --- Dev machine routes (X-Dev-Key header) ---
@app.get("/token")
def token():
    require_dev_key()
    access = get_valid_access_token()
    if not access:
        return jsonify({"error": "not_connected",
                        "message": "The owner must connect first at /"}), 409
    return jsonify({"access_token": access})


@app.route("/api/<path:endpoint>", methods=["GET", "POST"])
def api_proxy(endpoint):
    """Authenticated proxy: forward to the Teamleader API with the right token.

    Examples:
      POST /api/users.me
      POST /api/contacts.list   (optional JSON body)
    """
    require_dev_key()
    access = get_valid_access_token()
    if not access:
        return jsonify({"error": "not_connected",
                        "message": "The owner must connect first at /"}), 409

    url = f"{API_BASE}/{endpoint}"
    headers = {"Authorization": f"Bearer {access}"}
    if request.method == "POST":
        r = requests.post(url, headers=headers,
                          json=request.get_json(silent=True) or {}, timeout=30)
    else:
        r = requests.get(url, headers=headers, params=request.args, timeout=30)
    return Response(r.content, status=r.status_code,
                    content_type=r.headers.get("Content-Type", "application/json"))


# --- AWP Buro nacalculatie dashboard (extends this app with /app, /app/login, /beheer) ---
from nacalc import register_nacalc  # noqa: E402  (registered after app + helpers exist)
register_nacalc(app)


if __name__ == "__main__":
    # Local dev: python app.py  (Railway uses gunicorn via the Procfile)
    port = int(os.environ.get("PORT", "8765"))
    app.run(host="0.0.0.0", port=port, debug=True)
