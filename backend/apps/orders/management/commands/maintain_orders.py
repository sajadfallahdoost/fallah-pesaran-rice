"""Periodic maintenance. Run every 5 minutes (see docs/DEPLOYMENT.md).

1. Reconcile payment attempts whose verify never completed (customer closed the tab, gateway timeout).
2. Expire unpaid orders whose reservation window has passed, releasing their stock.

Reconciliation runs first so a payment that actually succeeded is applied before its order could expire.
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services.lifecycle import expire_order_if_due
from apps.payments.models import PaymentAttempt
from apps.payments.services import reconcile_attempt

logger = logging.getLogger(__name__)

RECONCILE_AFTER = timedelta(minutes=10)
RECONCILE_WINDOW = timedelta(days=3)


class Command(BaseCommand):
    help = "استعلام پرداخت‌های نیمه‌تمام و منقضی کردن سفارش‌های پرداخت‌نشده."

    def handle(self, *args, **options):
        now = timezone.now()
        pending = PaymentAttempt.objects.filter(
            status__in=[PaymentAttempt.Status.CREATED, PaymentAttempt.Status.REDIRECTED, PaymentAttempt.Status.UNKNOWN],
            created_at__lt=now - RECONCILE_AFTER,
            created_at__gt=now - RECONCILE_WINDOW,
        ).order_by("created_at")
        reconciled = 0
        for attempt in pending.iterator():
            try:
                before = attempt.status
                after = reconcile_attempt(attempt).status
                reconciled += before != after
            except Exception:  # one bad attempt must not stop the sweep
                logger.exception("reconcile failed for attempt %s", attempt.public_id)

        expired = 0
        due = Order.objects.filter(status=Order.Status.AWAITING_PAYMENT, reservation_expires_at__lte=now)
        for order_id in due.values_list("id", flat=True):
            try:
                expired += expire_order_if_due(order_id, now=now)
            except Exception:
                logger.exception("expire failed for order %s", order_id)

        self.stdout.write(f"maintain_orders: reconciled={reconciled} expired={expired}")
