"""Shared DRF plumbing: pagination, and a consistent error envelope.

Error responses always look like::

    {"error": {"code": "<machine_code>", "message": "<Persian message>", "fields": {...}}}
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class ApiError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid"

    def __init__(self, message: str, code: str = "invalid", status_code: int | None = None, fields=None):
        super().__init__(detail=message, code=code)
        self.error_code = code
        self.fields = fields or {}
        if status_code:
            self.status_code = status_code


class StorePagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 48

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_count": self.page.paginator.num_pages,
                "page_size": self.get_page_size(self.request),
                "results": data,
            }
        )


_DEFAULT_MESSAGES = {
    "not_found": "مورد درخواستی پیدا نشد.",
    "permission_denied": "اجازهٔ دسترسی به این بخش را ندارید.",
    "not_authenticated": "برای ادامه وارد حساب کاربری شوید.",
    "throttled": "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید.",
    "method_not_allowed": "این نوع درخواست پشتیبانی نمی‌شود.",
    "parse_error": "دادهٔ ارسالی قابل خواندن نیست.",
    "invalid": "اطلاعات واردشده معتبر نیست.",
}


def exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ApiError):
        payload = {"code": exc.error_code, "message": str(exc.detail), "fields": exc.fields}
    elif isinstance(exc, exceptions.ValidationError):
        fields = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
        payload = {"code": "invalid", "message": _DEFAULT_MESSAGES["invalid"], "fields": fields}
    else:
        code = getattr(exc, "default_code", "error")
        if code == "csrf_failed" or "CSRF" in str(getattr(exc, "detail", "")):
            code = "csrf_failed"
            message = "نشست شما منقضی شده است. صفحه را دوباره بارگذاری کنید."
        else:
            message = _DEFAULT_MESSAGES.get(code, str(getattr(exc, "detail", "")))
        payload = {"code": code, "message": message, "fields": {}}

    response.data = {"error": payload}
    return response
