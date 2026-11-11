"""Declared transition table for orders."""

from models import OrderStatus

ALLOWED_TRANSITIONS = {
    OrderStatus.DRAFT: [OrderStatus.SUBMITTED, OrderStatus.CANCELLED],
    OrderStatus.SUBMITTED: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED: [],
    OrderStatus.CANCELLED: [],
}
