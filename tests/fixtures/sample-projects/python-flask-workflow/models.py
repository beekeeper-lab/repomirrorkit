"""Order model with a status lifecycle."""

from enum import StrEnum

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class OrderStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.DRAFT)
