"""
Mini projet : tester un appel API en Python.

On utilise l'API publique gratuite JSONPlaceholder :
https://jsonplaceholder.typicode.com
Aucune clé API n'est nécessaire.
"""

import requests

# URL de base de l'API
BASE_URL = "https://jsonplaceholder.typicode.com"


def get_post(post_id: int) -> dict | None:
    """Récupère un post par son ID (requête GET)."""
    url = f"{BASE_URL}/posts/{post_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # lève une erreur si statut HTTP 4xx/5xx
    except requests.exceptions.RequestException as erreur:
        print(f"Erreur lors de l'appel API : {erreur}")
        return None

    return response.json()


def create_post(title: str, body: str, user_id: int) -> dict | None:
    """Crée un nouveau post (requête POST)."""
    url = f"{BASE_URL}/posts"
    donnees = {"title": title, "body": body, "userId": user_id}

    try:
        response = requests.post(url, json=donnees, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as erreur:
        print(f"Erreur lors de l'appel API : {erreur}")
        return None

    return response.json()


def main() -> None:
    print("=== 1) GET : récupérer un post ===")
    post = get_post(1)
    if post:
        print(f"Statut       : OK")
        print(f"ID           : {post['id']}")
        print(f"Titre        : {post['title']}")
        print(f"Contenu      : {post['body']}\n")

    print("=== 2) POST : créer un post ===")
    nouveau = create_post(
        title="Mon premier post",
        body="Ceci est un test d'appel API.",
        user_id=1,
    )
    if nouveau:
        print(f"Post créé avec l'ID : {nouveau['id']}")
        print(f"Réponse complète    : {nouveau}")


if __name__ == "__main__":
    main()
