from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.money import format_toman
from apps.payments.models import MockGatewayDecision
from apps.payments.services import available_providers, handle_return


class ProvidersView(APIView):
    def get(self, request):
        return Response(
            [
                {
                    "code": p.code,
                    "name": p.display_name,
                    "description": p.description,
                    "is_default": p.is_default,
                    "is_test": p.code == "MOCK",
                }
                for p in available_providers()
            ]
        )


@require_http_methods(["GET"])
def payment_return(request):
    """Client callback the library redirects to after its own verify step.

    Only reads persisted state; the query string never decides success.
    """
    attempt = handle_return(request.GET.get("attempt", ""), request.GET.get("tc", ""))
    if attempt is None:
        return HttpResponseRedirect(f"{settings.PUBLIC_BASE_URL}/checkout/result/unknown")
    order = attempt.order
    query = urlencode({"t": order.access_token, "attempt": str(attempt.public_id)})
    return HttpResponseRedirect(f"{settings.PUBLIC_BASE_URL}/checkout/result/{order.number}?{query}")


@require_http_methods(["GET", "POST"])
def mock_gateway(request):
    """Development-only simulated bank page. Returns 404 whenever the mock bank is disabled."""
    if not settings.PAYMENT_MOCK_ENABLED:
        raise Http404
    source = request.POST if request.method == "POST" else request.GET
    ref = source.get("ref", "")
    callback = source.get("callback", "")
    if not ref.startswith("MOCK-") or not callback:
        return HttpResponseBadRequest("invalid mock gateway request")
    # Only redirect back to this backend's own library callback.
    if urlparse(callback).path.rstrip("/") != "/bankgateways/callback":
        return HttpResponseBadRequest("invalid callback")

    if request.method == "POST":
        decision = request.POST.get("decision")
        if decision not in {"paid", "canceled", "failed", "timeout"}:
            return HttpResponseBadRequest("invalid decision")
        MockGatewayDecision.objects.update_or_create(reference_number=ref, defaults={"decision": decision})
        separator = "&" if "?" in callback else "?"
        return HttpResponseRedirect(f"{callback}{separator}{urlencode({'ref': ref})}")

    amount = int(source.get("amount", "0") or 0)
    return render(
        request,
        "payments/mock_gateway.html",
        {"ref": ref, "callback": callback, "amount": amount, "amount_display": format_toman(amount)},
    )
