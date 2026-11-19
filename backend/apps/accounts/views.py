from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Address
from apps.accounts.services import request_code, verify_code
from apps.core.api import ApiError
from apps.core.text import normalize_phone, normalize_postal_code, normalize_text
from apps.shipping.models import Province


def client_ip(request) -> str | None:
    # nginx sets X-Real-IP to the connecting client; never trust it without the proxy in front.
    if settings.TRUST_X_REAL_IP and request.META.get("HTTP_X_REAL_IP"):
        return request.META["HTTP_X_REAL_IP"]
    return request.META.get("REMOTE_ADDR")


class OtpRequestView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        phone = request_code(str(request.data.get("phone", "")), client_ip(request))
        return Response({"phone": phone, "expires_in": 120})


class OtpVerifyView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request):
        user = verify_code(request, str(request.data.get("phone", "")), str(request.data.get("code", "")))
        return Response({"phone": user.username})


class MeView(APIView):
    def get(self, request):
        if not request.user.is_authenticated or request.user.is_staff:
            return Response({"authenticated": False})
        return Response({"authenticated": True, "phone": request.user.username})


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"ok": True})


class AddressSerializer(serializers.ModelSerializer):
    province_id = serializers.PrimaryKeyRelatedField(source="province", queryset=Province.objects.all())
    province_name = serializers.CharField(source="province.name", read_only=True)

    class Meta:
        model = Address
        fields = (
            "id",
            "label",
            "full_name",
            "phone",
            "province_id",
            "province_name",
            "city",
            "address_line",
            "postal_code",
            "is_default",
        )

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not phone:
            raise serializers.ValidationError("شمارهٔ موبایل معتبر نیست.")
        return phone

    def validate_postal_code(self, value):
        value = normalize_postal_code(value)
        if value and len(value) != 10:
            raise serializers.ValidationError("کد پستی باید ۱۰ رقم باشد.")
        return value

    def validate_city(self, value):
        return normalize_text(value)

    def validate_address_line(self, value):
        value = normalize_text(value)
        if len(value) < 10:
            raise serializers.ValidationError("نشانی را کامل‌تر بنویسید.")
        return value


def _require_customer(request):
    if not request.user.is_authenticated:
        raise ApiError("ابتدا وارد حساب شوید.", code="not_authenticated", status_code=401)


class AddressListView(APIView):
    def get(self, request):
        _require_customer(request)
        return Response(AddressSerializer(request.user.addresses.select_related("province"), many=True).data)

    def post(self, request):
        _require_customer(request)
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.addresses.count() >= 10:
            raise ApiError("حداکثر ۱۰ نشانی می‌توانید ذخیره کنید.", code="limit")
        address = serializer.save(user=request.user)
        _ensure_single_default(request.user, address)
        return Response(AddressSerializer(address).data, status=201)


class AddressDetailView(APIView):
    def patch(self, request, pk: int):
        _require_customer(request)
        address = get_object_or_404(Address, pk=pk, user=request.user)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        address = serializer.save()
        _ensure_single_default(request.user, address)
        return Response(AddressSerializer(address).data)

    def delete(self, request, pk: int):
        _require_customer(request)
        get_object_or_404(Address, pk=pk, user=request.user).delete()
        return Response(status=204)


def _ensure_single_default(user, address: Address) -> None:
    if address.is_default:
        user.addresses.exclude(pk=address.pk).update(is_default=False)
