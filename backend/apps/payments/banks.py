"""Thin subclasses of library banks, registered through settings.CLASS."""

import requests
from azbankgateways.banks import Zarinpal as LibraryZarinpal
from azbankgateways.exceptions import BankGatewayConnectionError, BankGatewayRejectPayment
from azbankgateways.models import CurrencyEnum, PaymentStatus


class Zarinpal(LibraryZarinpal):
    """Use the same integer rial amount for both Zarinpal v4 calls."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_gateway_currency(CurrencyEnum.IRR)

    @classmethod
    def get_minimum_amount(cls):
        return 10 * super().get_minimum_amount()

    def verify_from_gateway(self, request):
        self.set_request(request)
        self.prepare_verify_from_gateway()
        if self._bank.status != PaymentStatus.REDIRECT_TO_BANK:
            return
        status = request.GET.get("Status")
        if status == "NOK":
            self._set_payment_status(PaymentStatus.CANCEL_BY_USER)
        elif status == "OK":
            self._set_payment_status(PaymentStatus.RETURN_FROM_BANK)
            self.verify(self.get_tracking_code())

    def verify(self, tracking_code):
        self.prepare_verify(tracking_code)
        result = self._send_data(self._verify_url, self.get_verify_data())["data"]
        if result and result.get("code") in (100, 101):
            reference = result.get("ref_id")
            if isinstance(reference, int) and reference > 0:
                # Keep Authority in reference_number for the library's callback lookup.
                self._bank.response_result = str(reference)
            self._set_payment_status(PaymentStatus.COMPLETE)
        else:
            self._set_payment_status(PaymentStatus.ERROR)

    def _send_data(self, api, data):
        # The library logs the entire payload on transport errors, including merchant_id.
        try:
            response = requests.post(api, json=data, timeout=self.get_timeout())
            if response.status_code >= 500:
                raise BankGatewayConnectionError()
            payload = response.json()
        except (requests.RequestException, ValueError):
            raise BankGatewayConnectionError() from None
        if not isinstance(payload, dict) or "data" not in payload:
            raise BankGatewayConnectionError()
        result = payload["data"]
        if result and not isinstance(result, dict):
            raise BankGatewayConnectionError()
        if api == self._payment_url and (not result or result.get("code") != 100 or not result.get("authority")):
            raise BankGatewayRejectPayment()
        return payload
