"""SQLAlchemy models for the sample Flask app."""

from __future__ import annotations

from enum import StrEnum

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """A user of the system."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), nullable=True, unique=True)
    role = db.Column(db.Enum("admin", "member", "guest", name="user_role"), nullable=False, default="member")
    __table_args__ = (db.CheckConstraint("length(name) > 0", name="name_not_empty"),)


class UserStatus(StrEnum):
    """Lifecycle states for a user account."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
