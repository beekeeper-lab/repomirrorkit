"""Sample Flask application — fixture for the harvester integration test."""

from __future__ import annotations

from flask import Flask, abort, jsonify, request
from models import User, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
db.init_app(app)


@app.route("/api/users", methods=["GET"])
def list_users():
    """Return all users as JSON."""
    users = User.query.all()
    return jsonify([{"id": u.id, "name": u.name} for u in users])


@app.route("/api/users", methods=["POST"])
def create_user():
    """Create a new user from the JSON request body."""
    data = request.get_json()
    user = User(name=data["name"], email=data.get("email"))
    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "name": user.name}), 201


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Return a single user, or 404 if no such user exists."""
    user = User.query.get(user_id)
    if user is None:
        abort(404, "User not found")
    return jsonify({"id": user.id, "name": user.name})
