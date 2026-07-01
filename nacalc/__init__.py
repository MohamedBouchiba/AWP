"""AWP Buro nacalculatie dashboard — extends the existing onboarding Flask app.

`register_nacalc(app)` initialises the SQLite store, bootstraps the admin user,
registers the dashboard blueprint, hardens the session cookie, and starts the
background sync thread. The existing onboarding/proxy routes are untouched.
"""
import os


def register_nacalc(app):
    from . import store, auth, sync
    from .views import bp

    store.init_db()
    auth.bootstrap_admin()
    app.register_blueprint(bp)

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
        app.config["SESSION_COOKIE_SECURE"] = True

    if not os.environ.get("NACALC_DISABLE_SYNC"):
        sync.start_background()
