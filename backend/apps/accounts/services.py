import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import OtpCode
from apps.accounts.sms import SmsError, send_otp
from apps.core.api import ApiError
from apps.core.text import normalize_digits, normalize_phone
from apps.orders.services.cart import SESSION_KEY, merge_guest_cart_into_user

RESEND_COOLDOWN = timedelta(seconds=60)
MAX_CODES_PER_PHONE_PER_HOUR = 5
MAX_CODES_PER_IP_PER_HOUR = 20


def request_code(raw_phone: str, ip: str | None) -> str:
    phone = normalize_phone(raw_phone)
    if not phone:
        raise ApiError("شمارهٔ موبایل معتبر نیست.", code="invalid_phone", fields={"phone": "نمونه: ۰۹۱۲۱۲۳۴۵۶۷"})
    now = timezone.now()
    hour_ago = now - timedelta(hours=1)
    recent = OtpCode.objects.filter(phone=phone, created_at__gt=hour_ago)
    last = recent.order_by("-created_at").first()
    if last and now - last.created_at < RESEND_COOLDOWN:
        wait = int((RESEND_COOLDOWN - (now - last.created_at)).total_seconds()) + 1
        raise ApiError(f"برای دریافت کد جدید {wait} ثانیه صبر کنید.", code="otp_cooldown", status_code=429)
    if recent.count() >= MAX_CODES_PER_PHONE_PER_HOUR or (
        ip and OtpCode.objects.filter(requester_ip=ip, created_at__gt=hour_ago).count() >= MAX_CODES_PER_IP_PER_HOUR
    ):
        raise ApiError("تعداد درخواست کد زیاد است. یک ساعت دیگر تلاش کنید.", code="otp_rate_limited", status_code=429)

    code = f"{secrets.randbelow(10**5):05d}"
    OtpCode.objects.create(
        phone=phone,
        code_hash=make_password(code),
        expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
        requester_ip=ip,
    )
    try:
        send_otp(phone, code)
    except SmsError as exc:
        raise ApiError("ارسال پیامک ممکن نشد. کمی بعد تلاش کنید.", code="sms_failed", status_code=503) from exc
    return phone


def verify_code(request, raw_phone: str, raw_code: str):
    phone = normalize_phone(raw_phone)
    code = normalize_digits(raw_code or "").strip()
    if not phone or not code.isdigit():
        raise ApiError("کد واردشده درست نیست.", code="invalid_code")

    # Errors are raised after the atomic block so the failed-attempt counter is committed.
    error = None
    with transaction.atomic():
        otp = (
            OtpCode.objects.select_for_update()
            .filter(phone=phone, consumed_at__isnull=True, expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )
        if otp is None:
            error = ApiError("کد منقضی شده است. کد جدید بگیرید.", code="code_expired")
        elif otp.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
            error = ApiError("تعداد تلاش‌ها زیاد بود. کد جدید بگیرید.", code="too_many_attempts", status_code=429)
        else:
            otp.attempts += 1
            if check_password(code, otp.code_hash):
                otp.consumed_at = timezone.now()
            else:
                error = ApiError("کد واردشده درست نیست.", code="invalid_code")
            otp.save(update_fields=["attempts", "consumed_at"])
    if error:
        raise error

    User = get_user_model()
    user, created = User.objects.get_or_create(username=phone, defaults={"is_active": True})
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    if not user.is_active:
        raise ApiError("این حساب غیرفعال است.", code="inactive", status_code=403)
    if user.is_staff:
        # Staff sign in through the protected admin with a password, not SMS.
        raise ApiError("ورود کارکنان فقط از پنل مدیریت ممکن است.", code="staff_account", status_code=403)
    guest_token = request.session.get(SESSION_KEY)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    merge_guest_cart_into_user(request, guest_token)
    return user
