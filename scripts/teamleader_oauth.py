"""
Test de connexion OAuth2 a l'API Teamleader Focus.
Lance un serveur local, ouvre le navigateur pour l'autorisation,
echange le code contre un token et appelle users.me.

Prerequis:
  - pip install requests
  - la redirect_uri ci-dessous doit etre whitelistee dans les
    parametres de l'integration (page Build du Marketplace).
"""

import os
import json
import http.server
import socketserver
import urllib.parse
import webbrowser
import requests

TOKENS_FILE = "tokens.json"

# --- Identifiants : UNIQUEMENT via variables d'environnement (jamais en dur) ---
#   PowerShell : $env:TL_CLIENT_ID = "..."; $env:TL_CLIENT_SECRET = "..."
CLIENT_ID = os.environ.get("TL_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TL_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    raise SystemExit(
        "TL_CLIENT_ID / TL_CLIENT_SECRET manquants. "
        "Definis-les en variables d'environnement avant de lancer ce script."
    )

PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}/oauth/callback"

AUTHORIZE_URL = "https://focus.teamleader.eu/oauth2/authorize"
TOKEN_URL = "https://focus.teamleader.eu/oauth2/access_token"
API_BASE = "https://api.focus.teamleader.eu"
STATE = "test123"

_auth_code = None


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if params.get("state", [None])[0] != STATE:
            self.wfile.write("State invalide, requete ignoree.".encode())
            return
        if "code" in params:
            _auth_code = params["code"][0]
            self.wfile.write("OK, tu peux fermer cet onglet.".encode())
        elif "error" in params:
            self.wfile.write(f"Erreur: {params['error'][0]}".encode())

    def log_message(self, *args):
        pass  # silence


class _ReuseServer(socketserver.TCPServer):
    allow_reuse_address = True


def get_auth_code():
    qs = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": STATE,
    })
    auth_url = f"{AUTHORIZE_URL}?{qs}"
    server = _ReuseServer(("localhost", PORT), _Handler)
    print("Ouverture du navigateur. Si rien ne s'ouvre, va sur:\n", auth_url, "\n")
    webbrowser.open(auth_url)
    while _auth_code is None:
        server.handle_request()
    server.server_close()
    return _auth_code


def main():
    code = get_auth_code()
    print("Code recu:", code)

    resp = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    if resp.status_code != 200:
        print("Echec echange token:", resp.status_code, resp.text)
        return

    tokens = resp.json()
    access = tokens["access_token"]

    # Sauvegarde des tokens pour reutilisation (le refresh_token sert au dev)
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    print(f"\nTokens sauvegardes dans '{TOKENS_FILE}'.")

    print("Access token OK (expire dans", tokens.get("expires_in"), "s)")
    print("Refresh token:", tokens.get("refresh_token"))

    me = requests.post(f"{API_BASE}/users.me",
                       headers={"Authorization": f"Bearer {access}"})
    print("\nusers.me ->", me.status_code)
    print(me.json())


if __name__ == "__main__":
    main()
