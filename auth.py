from functools import wraps

from flask import redirect, session, url_for, g

from db import get_db


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Return the current user row, or None."""
    if "user" not in g:
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = get_db().execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    return g.user
