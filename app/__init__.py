from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_toastr import Toastr

from config import Config

db = SQLAlchemy()
migrate = Migrate()
toastr = Toastr()

login_manager = LoginManager()
login_manager.login_view = 'azure.login'


def create_app(config=Config):
    app = Flask(__name__)

    app.config.from_object(config)

    db.init_app(app)

    toastr.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        if db.engine.url.drivername == 'sqlite':
            migrate.init_app(app, db, render_as_batch=True)
        else:
            migrate.init_app(app, db)

    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.main import main as main_bp
    app.register_blueprint(main_bp)

    return app


from app import models
