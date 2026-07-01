# 🚀 Lancer le projet en local — en 5 étapes

Ce guide permet à **n'importe qui** de faire tourner le dashboard sur son ordinateur,
**sans connaître le code**. L'idée : tu installes un éditeur avec une IA, tu lui colles
**un seul prompt**, et l'IA fait tout le reste (installation, configuration, démarrage).

> ℹ️ En local, le dashboard tourne en **mode démo** : l'interface complète s'affiche, mais
> les données sont vides (il n'est pas connecté à Teamleader). C'est normal et voulu.

---

## Étape 1 — Installer Antigravity

Télécharge et installe **Antigravity** depuis son site officiel, puis ouvre-le.

## Étape 2 — Ajouter l'extension Claude Code + connecter ton compte

1. Dans Antigravity, ouvre le panneau **Extensions** (icône des extensions dans la barre latérale).
2. Cherche **« Claude Code »** et clique sur **Installer**.
3. Ouvre Claude Code et **connecte-toi avec ton compte Claude** (Anthropic) quand c'est demandé.

## Étape 3 — Ouvrir le projet dans Antigravity

- **File → Open Folder** et choisis un dossier vide (ex. `Documents/AWP`).
- *(Tu n'as pas besoin de télécharger le projet à la main : le prompt de l'étape 4 le
  clonera tout seul depuis GitHub.)*

## Étape 4 — Coller LE prompt à Claude Code

Ouvre la conversation Claude Code et **copie-colle exactement le texte ci-dessous**, puis
valide. L'IA va tout installer, configurer, vérifier et démarrer le serveur.

```text
Tu es mon assistant de développement. Objectif : lancer ce projet Python (Flask) en local
sur ma machine, sans que je touche au code. Fais TOUT toi-même, étape par étape, et corrige
seul les erreurs que tu rencontres. Explique chaque action en une phrase simple.

Contexte : c'est le dashboard « nacalculatie » d'AWP Buro (une app Flask). Il n'a PAS besoin
de se connecter à Teamleader pour tourner en local — on le lance en mode démo (interface
complète, données vides).

Étapes à réaliser :
1. Si le projet n'est pas déjà présent dans ce dossier, clone-le puis place-toi dedans :
   git clone https://github.com/MohamedBouchiba/AWP.git
2. Lis les fichiers README.md et docs/HANDOFF.md pour comprendre le projet.
3. Vérifie que Python 3.10 ou plus est installé (python --version). S'il manque, dis-moi en
   une phrase comment l'installer, puis arrête-toi.
4. Crée un environnement virtuel et installe les dépendances. Utilise ensuite le Python de
   cet environnement pour toutes les commandes suivantes :
   python -m venv .venv   →   active-le   →   pip install -r requirements.txt
5. Configure ces variables d'environnement (adapte la syntaxe à mon système d'exploitation) :
   NACALC_DISABLE_SYNC = 1
   SECRET_KEY = dev-secret-local
   DATA_DIR = .devdata
   BOOTSTRAP_ADMIN_EMAIL = admin@local.test
   BOOTSTRAP_ADMIN_PASSWORD = demo1234
6. Lance le test de santé : python scripts/smoke_test.py
   Toutes les pages doivent renvoyer 200 (et 302 pour /app quand on n'est pas connecté).
   Si ça échoue, corrige la cause et relance jusqu'à ce que ce soit vert.
7. Démarre le serveur : python app.py
8. Donne-moi clairement, à la fin :
   - l'URL à ouvrir : http://localhost:8765/app
   - l'email et le mot de passe pour me connecter : admin@local.test / demo1234
   - comment arrêter le serveur (Ctrl+C).
9. Rappelle-moi que le dashboard est vide car il n'est pas connecté à Teamleader — c'est
   normal en local. Pour de vraies données, il faut la configuration OAuth de docs/DEPLOY.md.

Si une commande échoue (dépendance manquante, port déjà utilisé, mauvaise version de Python,
environnement virtuel non activé, etc.), diagnostique la cause, corrige-la toi-même, et
continue jusqu'à ce que l'application tourne. À la fin, confirme que le serveur tourne et
attends mes questions.
```

## Étape 5 — Ouvrir le dashboard

Quand l'IA te dit que le serveur tourne :

1. Ouvre ton navigateur sur **http://localhost:8765/app**
2. Connecte-toi avec :
   - **E-mail :** `admin@local.test`
   - **Mot de passe :** `demo1234`

Tu vois le dashboard 🎉 (vide, car en mode démo). Pour l'arrêter : reviens dans Claude Code
et fais **Ctrl + C**.

---

## En cas de souci

- **« python n'est pas reconnu »** → Python n'est pas installé. Demande à l'IA : *« installe
  Python 3.12 et recommence »*, ou installe-le depuis python.org.
- **« port 8765 déjà utilisé »** → demande à l'IA : *« lance sur le port 8080 à la place »*
  (elle mettra la variable `PORT=8080`).
- **La page ne charge pas** → vérifie que la fenêtre Claude Code affiche bien
  *« Running on http://…:8765 »* et qu'elle n'a pas d'erreur rouge ; sinon, demande à l'IA de
  relancer.
- **Tu veux les vraies données Teamleader** → ce n'est pas nécessaire pour tester en local ;
  la marche à suivre complète est dans [`DEPLOY.md`](DEPLOY.md).
