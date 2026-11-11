from flask import Blueprint, jsonify, request

from shop.extensions import db
from shop.models import Item

bp = Blueprint("items", __name__, url_prefix="/items")


@bp.get("/")
def list_items():
    return jsonify([{"id": i.id, "name": i.name} for i in Item.query.all()])


@bp.post("/")
def create_item():
    data = request.get_json()
    if not data.get("name"):
        return jsonify({"error": "name required"}), 400
    item = Item(name=data["name"], price=data.get("price", 0))
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id, "name": item.name}), 201


@bp.delete("/<int:item_id>")
def delete_item(item_id):
    Item.query.filter_by(id=item_id).delete()
    db.session.commit()
    return "", 204
