from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin

from app import db, login_manager


class Role(db.Model, UserMixin):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(1028))
    department = db.Column(db.String(1028))
    position = db.Column(db.String(1028))
    email = db.Column(db.String(1028))
    name = db.Column(db.String(1028))
    role_id = db.Column(db.Integer, db.ForeignKey(Role.id), default=1)
    supervisor = db.Column(db.String)


class OAuth(OAuthConsumerMixin, db.Model):
    __tablename__ = 'oauth'

    provider_user_id = db.Column(db.String(1028), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
