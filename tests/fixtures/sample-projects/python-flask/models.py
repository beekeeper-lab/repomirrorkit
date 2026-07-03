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
    email = db.Column(db.String(255), nullable=True)


class UserStatus(StrEnum):
    """Lifecycle states for a user account."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
