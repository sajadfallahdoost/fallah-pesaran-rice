"""Thin subclasses of library banks, registered through settings.CLASS."""

from azbankgateways.banks import Zarinpal as LibraryZarinpal
from azbankgateways.exceptions import AmountDoesNotSupport


class Zarinpal(LibraryZarinpal):
    """Zarinpal takes toman; the library converts rial with true division and would send 15000.0."""

    def prepare_amount(self):
        super().prepare_amount()
        amount = self._gateway_amount
        if isinstance(amount, float):
            if not amount.is_integer():
                raise AmountDoesNotSupport()
            self._gateway_amount = int(amount)
