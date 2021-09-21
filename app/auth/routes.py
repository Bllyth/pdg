from flask import flash, redirect, url_for, render_template, session, request
from flask_dance.consumer import oauth_authorized, oauth_error, oauth_before_login
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.contrib.azure import azure
from flask_login import current_user, login_user, login_required, logout_user
from oauthlib.oauth2 import InvalidGrantError, TokenExpiredError
from sqlalchemy.exc import NoResultFound

from . import auth
from .. import db
from ..models.users import OAuth, User

auth.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user)


# @oauth_before_login.connect
# def before_login(auth, url):
#     session["next_url"] = request.args.get("next_url")

@auth.route("/login")
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.pdgs'))
    return render_template('auth/login.html')


@oauth_authorized.connect_via(auth)
def azure_logged_in(auth, token):
    if not token:
        print(token)
        flash("Failed to log in with azure.", category="error")
        return False

    # print(token)

    resps = auth.session.get("/v1.0/users?$top=500")
    if not resps.ok:
        print(resps)
        msg = "Failed to fetch user info from Azure."
        flash(msg, category="error")
        return False

    azure_infos = resps.json()
    for key in azure_infos['value']:
        user = User.query.filter_by(name=key["userPrincipalName"]).first()
        if not user:
            user = User(
                # create user with user information from Microsoft Graph
                email=key["mail"],
                username=key["displayName"],
                name=key["userPrincipalName"],
                position=key["jobTitle"],
                department=key["jobTitle"]
            )
            db.session.add(user)
            db.session.commit()

    resp2 = auth.session.get("/v1.0/me/manager")

    manager_info = resp2.json()
    if not resp2.ok:
        print(resp2)
        msg = "Failed to fetch user info from Azure."
        flash(msg, category="error")
        return False

    # print(manager_info)

    manager_email = manager_info["mail"]

    resp = auth.session.get("/v1.0/me")

    azure_info = resp.json()
    if not resp.ok:
        print(resp)
        msg = "Failed to fetch user info from Azure."
        flash(msg, category="error")
        return False
    # print(azure_info)
    azure_user_id = str(azure_info["id"])
    user = User.query.filter_by(name=azure_info["userPrincipalName"]).first()
    user.supervisor = manager_email
    db.session.commit()

    # Find this OAuth token in the database, or create it
    query = OAuth.query.filter_by(
        provider=auth.name,
        provider_user_id=azure_user_id,
    )
    try:
        oauth = query.one()
    except NoResultFound:
        oauth = OAuth(
            provider=auth.name,
            provider_user_id=azure_user_id,
            token=token,
        )

    if oauth.user:
        login_user(oauth.user)
        flash("Successfully signed in with Azure.")

    else:

        oauth.user = user
        # Save and commit our database models
        db.session.add(oauth)
        db.session.commit()
        # Log in the new local user account
        login_user(user)
        flash("Successfully signed in with Azure.")

    # # Disable Flask-Dance's default behavior for saving the OAuth token
    return False


# notify on OAuth provider error
@oauth_error.connect_via(auth)
def azure_error(auth, error, error_description=None, error_uri=None):
    msg = (
        "OAuth error from {name}! "
        "error={error} description={description} uri={uri}"
    ).format(
        name=auth.name,
        error=error,
        description=error_description,
        uri=error_uri,
    )
    flash(msg, category="error")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out")
    return redirect(url_for("azure.user_login"))

# @auth.route("/users")
# @login_required
# def users():
#     # if not azure.authorized:
#     #     return redirect(url_for('azure.login'))
#
#     try:
#         resp = auth.session.get("/v1.0/users")
#         # assert resp.ok, resp.text
#     except (InvalidGrantError, TokenExpiredError) as e:  # or maybe any OAuth2Error
#         return redirect(url_for("azure.login"))
#
#     if resp.ok:
#         print(resp)
#         msg = "Failed to fetch user info from Azure."
#         flash(msg, category="error")
#         return False
#
#     azure_infos = resp.json()
#
#     print('Hello', azure_infos['value'])
#     # for key in azure_infos['value']:
#     #     for d in key:
#     #         print(d.get('id'))
#     # azure_user_id = azure_info[0]
#     # print('Azure', azure_user_id)
#     # # Find this OAuth token in the database, or create it
#     # query = OAuth.query.filter_by(
#     #     provider=auth.name,
#     #     provider_user_id=azure_user_id,
#     # )
#     # try:
#     #     oauth = query.one()
#     # except NoResultFound:
#     #     oauth = OAuth(
#     #         provider=auth.name,
#     #         provider_user_id=azure_user_id,
#     #         token=token,
#     #     )
#     #
#     # if oauth.user:
#     #     login_user(oauth.user)
#     #     flash("Successfully signed in with Azure.")
#     #
#     # else:
#     #     # Create a new local user account for this user
#     #     user = User(
#     #         # create user with user information from Microsoft Graph
#     #         email=azure_info["mail"],
#     #         username=azure_info["displayName"],
#     #         name=azure_info["userPrincipalName"]
#     #     )
#     #
#     #     print('Hello')
#     #     # Associate the new local user account with the OAuth token
#     #     oauth.user = user
#     #     # Save and commit our database models
#     #     db.session.add_all([user, oauth])
#     #     db.session.commit()
#     #     # Log in the new local user account
#     #     login_user(user)
#     #     flash("Successfully signed in with Azure.")
#     # return render_template("test.html")
#     return 'Hello'
