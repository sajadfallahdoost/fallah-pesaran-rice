"""Development-only bank for az-iranian-bank-gateways.

It goes through the library's real lifecycle (ready → get_gateway → library callback view
→ verify_from_gateway → verify → client callback) without contacting any provider. The
outcome is chosen on a local simulated gateway page and read back server-side during
verify, so a query parameter can never mark a payment as successful.

Registered in settings.CLASS only when PAYMENT_MOCK_ENABLED (never in production).
"""

import uuid

from azbankgateways.banks import BaseBank
from azbankgateways.exceptions.exceptions import BankGatewayConnectionError
from azbankgateways.models import CurrencyEnum, PaymentStatus
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse


class MockBank(BaseBank):
    def __init__(self, **kwargs):
        if not settings.PAYMENT_MOCK_ENABLED:
            raise ImproperlyConfigured("Mock bank is disabled.")
        super().__init__(**kwargs)
        self.set_gateway_currency(CurrencyEnum.IRR)

    def get_bank_type(self):
        return "MOCK"

    def set_default_settings(self):
        pass

    def get_pay_data(self):
        return {"amount": self.get_gateway_amount(), "callback_url": self._get_gateway_callback_url()}

    def prepare_pay(self):
        super().prepare_pay()

    def pay(self):
        super().pay()
        self._set_reference_number(f"MOCK-{uuid.uuid4().hex[:20]}")
        self._set_transaction_status_text("mock gateway session created")

    def _get_gateway_payment_url_parameter(self):
        url = reverse("payments:mock-gateway")
        request = self.get_request()
        return request.build_absolute_uri(url) if request else url

    def _get_gateway_payment_parameter(self):
        return {
            "ref": self.get_reference_number(),
            "amount": str(self.get_gateway_amount()),
            "callback": self._get_gateway_callback_url(),
        }

    def _get_gateway_payment_method_parameter(self):
        return "GET"

    def prepare_verify_from_gateway(self):
        super().prepare_verify_from_gateway()
        self._set_reference_number(self.get_request().GET.get("ref", ""))
        self._set_bank_record()

    def verify_from_gateway(self, request):
        super().verify_from_gateway(request)

    def get_verify_data(self):
        return {"ref": self.get_reference_number()}

    def prepare_verify(self, tracking_code):
        super().prepare_verify(tracking_code)

    def verify(self, tracking_code):
        from apps.payments.models import MockGatewayDecision

        super().verify(tracking_code)
        decision = (
            MockGatewayDecision.objects.filter(reference_number=self.get_reference_number())
            .values_list("decision", flat=True)
            .first()
        )
        if decision == "timeout":
            # Simulates a verify call that never got an answer: status stays RETURN_FROM_BANK.
            raise BankGatewayConnectionError()
        if decision == "paid":
            self._set_payment_status(PaymentStatus.COMPLETE)
        elif decision == "failed":
            self._set_payment_status(PaymentStatus.ERROR)
        else:
            self._set_payment_status(PaymentStatus.CANCEL_BY_USER)
