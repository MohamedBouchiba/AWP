"""
Script pour le DEV : utilise le refresh_token (obtenu une seule fois via
l'autorisation du owner) pour recuperer un access_token frais, puis appeler
l'API Teamleader. A lancer autant de fois que voulu, sans le owner.

Prerequis : le fichier 'tokens.json' doit exister
(genere par teamleader_oauth.py apres l'autorisation du owner).

Note : Teamleader fait tourner (rotate) le refresh_token a chaque rafraichissement.
Ce script re-sauvegarde donc le nouveau jeu de tokens a chaque execution.
"""

import json
import sys

import requests

from teamleader_oauth import CLIENT_ID, CLIENT_SECRET, TOKEN_URL, API_BASE, TOKENS_FILE


def load_tokens() -> dict:
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(
            f"'{TOKENS_FILE}' introuvable.\n"
            "-> Le owner doit d'abord autoriser l'integration via "
            "'python teamleader_oauth.py'."
        )
        sys.exit(1)


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }, timeout=15)
    if resp.status_code != 200:
        print("Echec du refresh:", resp.status_code, resp.text)
        print("-> Le refresh_token est peut-etre revoque/expire. "
              "Demande au owner de re-autoriser.")
        sys.exit(1)
    return resp.json()


def main() -> None:
    tokens = load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("Aucun refresh_token dans tokens.json.")
        sys.exit(1)

    # 1) Obtenir un access_token frais
    new_tokens = refresh_access_token(refresh_token)

    # 2) Re-sauvegarder (le refresh_token a peut-etre change : rotation)
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(new_tokens, f, indent=2)

    access = new_tokens["access_token"]
    print("Access token rafraichi (expire dans",
          new_tokens.get("expires_in"), "s)\n")

    # 3) Exemple d'appel API : users.me
    me = requests.post(f"{API_BASE}/users.me",
                       headers={"Authorization": f"Bearer {access}"},
                       timeout=15)
    print("users.me ->", me.status_code)
    print(json.dumps(me.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
