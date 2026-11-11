from flask import Flask, abort, jsonify, request
from models import Order, OrderStatus, db

app = Flask(__name__)
db.init_app(app)


def _require(order, *allowed):
    if order.status not in allowed:
        abort(409)


@app.post("/api/orders")
def create_order():
    data = request.get_json()
    order = Order(customer=data["customer"], status=OrderStatus.DRAFT)
    db.session.add(order)
    db.session.commit()
    return jsonify({"id": order.id, "status": order.status}), 201


@app.post("/api/orders/<int:order_id>/submit")
def submit_order(order_id):
    order = db.get_or_404(Order, order_id)
    if order.status != OrderStatus.DRAFT:
        abort(409)
    order.status = OrderStatus.SUBMITTED
    db.session.commit()
    return jsonify({"id": order.id, "status": order.status})


@app.post("/api/orders/<int:order_id>/pay")
def pay_order(order_id):
    order = db.get_or_404(Order, order_id)
    if order.status == OrderStatus.SUBMITTED:
        order.status = OrderStatus.PAID
    else:
        abort(409)
    db.session.commit()
    return jsonify({"id": order.id, "status": order.status})
