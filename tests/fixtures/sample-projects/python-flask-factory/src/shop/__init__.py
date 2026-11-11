"""Shop app factory — fixture with blueprints, verb shorthand, nested routes."""

from flask import Flask

from shop.extensions import db
from shop.items import bp as items_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shop.db"
    db.init_app(app)
    app.register_blueprint(items_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
