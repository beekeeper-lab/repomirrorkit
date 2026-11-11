"""Orders API used as a runnable parity fixture (validation, auth, workflow, lookup)."""

from __future__ import annotations

import os

from flask import Flask, jsonify, request
from models import Category, Order, OrderStatus, db

API_KEY = os.environ.get("API_KEY", "demo-key")
SEED_CATEGORIES = ["books", "games", "music"]


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    db.init_app(app)

    with app.app_context():
        db.create_all()
        for name in SEED_CATEGORIES:
            db.session.add(Category(name=name))
        db.session.commit()

    def unauthorized():
        return jsonify({"error": "unauthorized"}), 401

    def authed() -> bool:
        return request.headers.get("X-API-Key") == API_KEY

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/categories")
    def list_categories():
        rows = Category.query.order_by(Category.id).all()
        return jsonify([{"id": c.id, "name": c.name} for c in rows])

    @app.get("/api/orders")
    def list_orders():
        rows = Order.query.order_by(Order.id).all()
        return jsonify([o.to_dict() for o in rows])

    @app.post("/api/orders")
    def create_order():
        if not authed():
            return unauthorized()
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "invalid json"}), 400
        customer = data.get("customer")
        if not isinstance(customer, str) or len(customer.strip()) < 2:
            return jsonify({"error": "customer must be at least 2 characters"}), 400
        category_id = data.get("category_id")
        if not isinstance(category_id, int) or db.session.get(Category, category_id) is None:
            return jsonify({"error": "unknown category"}), 400
        order = Order(customer=customer.strip(), category_id=category_id, status=OrderStatus.DRAFT)
        db.session.add(order)
        db.session.commit()
        return jsonify(order.to_dict()), 201

    @app.get("/api/orders/<int:order_id>")
    def get_order(order_id):
        order = db.session.get(Order, order_id)
        if order is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(order.to_dict())

    def transition(order_id, allowed, target):
        if not authed():
            return unauthorized()
        order = db.session.get(Order, order_id)
        if order is None:
            return jsonify({"error": "not found"}), 404
        if order.status not in allowed:
            return jsonify({"error": "invalid transition"}), 409
        order.status = target
        db.session.commit()
        return jsonify(order.to_dict())

    @app.post("/api/orders/<int:order_id>/submit")
    def submit_order(order_id):
        return transition(order_id, {OrderStatus.DRAFT}, OrderStatus.SUBMITTED)

    @app.post("/api/orders/<int:order_id>/pay")
    def pay_order(order_id):
        return transition(order_id, {OrderStatus.SUBMITTED}, OrderStatus.PAID)

    @app.post("/api/orders/<int:order_id>/cancel")
    def cancel_order(order_id):
        return transition(
            order_id, {OrderStatus.DRAFT, OrderStatus.SUBMITTED}, OrderStatus.CANCELLED
        )

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
