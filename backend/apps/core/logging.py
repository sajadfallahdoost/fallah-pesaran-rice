"""Log redaction for merchant credentials.

The gateway library logs request payloads (including merchant ids) on errors.
"""

import logging
import os

_SECRET_ENV_VARS = (
    "ZARINPAL_MERCHANT_CODE",
    "ZIBAL_MERCHANT_CODE",
    "SEP_MERCHANT_CODE",
    "SEP_TERMINAL_CODE",
    "MELLAT_TERMINAL_CODE",
    "MELLAT_USERNAME",
    "MELLAT_PASSWORD",
    "BMI_MERCHANT_CODE",
    "BMI_TERMINAL_CODE",
    "BMI_SECRET_KEY",
    "KAVENEGAR_API_KEY",
    "DJANGO_SECRET_KEY",
)


class RedactSecretsFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self._secrets = [v for v in (os.environ.get(k, "") for k in _SECRET_ENV_VARS) if len(v) >= 6]

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secrets:
            return True
        message = record.getMessage()
        redacted = message
        for secret in self._secrets:
            redacted = redacted.replace(secret, "***")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True
