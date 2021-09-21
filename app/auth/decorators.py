from functools import wraps

from flask import url_for, redirect, session, request
from flask_dance.contrib.azure import azure

from . import auth


def login_required(func):
    """Enforces authentication on a route."""

    @wraps(func)
    def decorated_route(*args, **kwargs):
        token = auth.session.token

        if not azure.authorized:
            session["next_url"] = request.path
            return redirect(url_for('azure.login'))
        # We are authorized, do things
        return func(*args, **kwargs)

    return decorated_route
