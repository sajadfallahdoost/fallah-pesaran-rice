"""SMS delivery for login codes.

- console: development only; prints the code to the server log. Refused in production by settings.
- kavenegar: Kavenegar "verify/lookup" API with an approved template (KAVENEGAR_OTP_TEMPLATE).
"""

import logging

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class SmsError(Exception):
    pass


def send_otp(phone: str, code: str) -> None:
    backend = settings.SMS_BACKEND
    if backend == "console":
        if settings.IS_PRODUCTION:
            raise ImproperlyConfigured("console SMS backend is not allowed in production")
        logger.warning("DEV OTP for %s: %s", phone, code)
        return
    if backend == "kavenegar":
        _send_kavenegar(phone, code)
        return
    raise ImproperlyConfigured(f"Unknown SMS_BACKEND {backend!r}")


def _send_kavenegar(phone: str, code: str) -> None:
    api_key = settings.KAVENEGAR_API_KEY
    template = settings.KAVENEGAR_OTP_TEMPLATE
    if not api_key or not template:
        raise SmsError("Kavenegar is not configured")
    url = f"https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"
    try:
        response = requests.post(url, data={"receptor": phone, "token": code, "template": template}, timeout=8)
    except requests.RequestException as exc:
        raise SmsError("SMS provider unreachable") from exc
    if response.status_code != 200:
        raise SmsError(f"SMS provider returned HTTP {response.status_code}")
