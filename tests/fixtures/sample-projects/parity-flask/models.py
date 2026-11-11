"""Data model for the parity fixture: orders with a status lifecycle."""

from __future__ import annotations

from enum import StrEnum

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class OrderStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PAID = "paid"
    CANCELLED = "cancelled"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False, unique=True)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer = db.Column(db.String(80), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.DRAFT)

    def to_dict(self):
        return {
            "id": self.id,
            "customer": self.customer,
            "category_id": self.category_id,
            "status": self.status,
        }
