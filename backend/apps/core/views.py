from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.serializers import CategorySerializer, ProductCardSerializer
from apps.catalog.views import categories_with_counts, published_products
from apps.core.models import FAQ, HomeBanner, Page, StoreSettings


def store_payload(store: StoreSettings) -> dict:
    return {
        "name": store.store_name,
        "tagline": store.tagline,
        "phone": store.phone,
        "email": store.email,
        "telegram_username": store.telegram_username,
        "address": store.address,
        "business_hours": store.business_hours,
        "announcement": store.announcement,
        "sales_enabled": store.sales_enabled,
        "seo_title": store.seo_title,
        "seo_description": store.seo_description,
    }


class SiteView(APIView):
    """Header/footer data used on every page."""

    def get(self, request):
        nav = [
            c for c in categories_with_counts().filter(show_in_navigation=True) if c.product_count or c.show_when_empty
        ]
        pages = Page.objects.filter(is_published=True).values("slug", "title")
        return Response(
            {
                "store": store_payload(StoreSettings.load()),
                "navigation": [{"name": c.name, "slug": c.slug, "product_count": c.product_count} for c in nav],
                "pages": list(pages),
                # Shown as a site-wide notice: no real money moves and/or sample products are listed.
                "demo_mode": settings.PAYMENT_MOCK_ENABLED or published_products().filter(is_sample=True).exists(),
            }
        )


class HomeView(APIView):
    def get(self, request):
        banners = HomeBanner.objects.filter(is_active=True)
        categories = [c for c in categories_with_counts() if c.product_count or c.show_when_empty]
        featured = published_products().filter(is_featured=True)[:6]
        context = {"now": timezone.now()}
        return Response(
            {
                "banners": [
                    {
                        "title": b.title,
                        "subtitle": b.subtitle,
                        "eyebrow": b.eyebrow,
                        "image_desktop": b.image_desktop.url if b.image_desktop else None,
                        "image_mobile": b.image_mobile.url if b.image_mobile else None,
                        "image_alt": b.image_alt,
                        "cta_label": b.cta_label,
                        "cta_url": b.cta_url,
                        "is_generated_sample": b.is_generated_sample,
                    }
                    for b in banners
                ],
                "categories": CategorySerializer(categories, many=True).data,
                "featured": ProductCardSerializer(featured, many=True, context=context).data,
                "faqs": list(FAQ.objects.filter(is_active=True).values("question", "answer")[:4]),
            }
        )


class PageView(APIView):
    def get(self, request, slug):
        page = get_object_or_404(Page, slug=slug, is_published=True)
        return Response(
            {
                "slug": page.slug,
                "title": page.title,
                "summary": page.summary,
                "body": page.body,
                "requires_owner_review": page.requires_owner_review,
                "seo_title": page.seo_title,
                "seo_description": page.seo_description,
                "updated_at": page.updated_at,
            }
        )


class FaqView(APIView):
    def get(self, request):
        return Response(list(FAQ.objects.filter(is_active=True).values("group", "question", "answer")))


class CsrfView(APIView):
    """Sets the csrftoken cookie; the storefront echoes it in X-CSRFToken."""

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"ok": True})


def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
