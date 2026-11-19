from django.db.models import Count, Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.catalog.serializers import CategorySerializer, ProductCardSerializer, ProductDetailSerializer
from apps.core.text import normalize_text


def published_products():
    return (
        Product.objects.published()
        .select_related("category")
        .prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.order_by("sort_order", "id")),
            Prefetch("variants", queryset=ProductVariant.objects.order_by("sort_order", "package_amount")),
        )
    )


def categories_with_counts():
    return (
        Category.objects.filter(is_active=True)
        .annotate(product_count=Count("products", filter=Q(products__status=Product.Status.PUBLISHED)))
        .order_by("sort_order", "name")
    )  # Meta.ordering is not applied to aggregated querysets


class CategoryListView(APIView):
    def get(self, request):
        categories = [c for c in categories_with_counts() if c.product_count or c.show_when_empty]
        return Response(CategorySerializer(categories, many=True).data)


class CategoryDetailView(APIView):
    def get(self, request, slug):
        category = get_object_or_404(categories_with_counts(), slug=slug)
        return Response(CategorySerializer(category).data)


class ProductListView(ListAPIView):
    serializer_class = ProductCardSerializer
    SORTS = {
        "newest": ("-published_at", "name"),
        "price_asc": ("min_price", "name"),
        "price_desc": ("-min_price", "name"),
        "featured": ("sort_order", "-published_at"),
    }

    def get_queryset(self):
        params = self.request.query_params
        qs = published_products().annotate(min_price=Min("variants__price", filter=Q(variants__is_active=True)))
        if category := params.get("category"):
            qs = qs.filter(category__slug=category)
        if query := normalize_text(params.get("q", ""))[:80]:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(short_description__icontains=query)
                | Q(category__name__icontains=query)
                | Q(attributes__value__icontains=query)
            ).distinct()
        if params.get("in_stock") in {"1", "true"}:
            qs = qs.filter(variants__is_active=True, variants__stock__gt=0).distinct()
        if params.get("featured") in {"1", "true"}:
            qs = qs.filter(is_featured=True)
        return qs.order_by(*self.SORTS.get(params.get("sort", "featured"), self.SORTS["featured"]))

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "now": timezone.now()}


class ProductDetailView(APIView):
    def get(self, request, slug):
        product = get_object_or_404(
            published_products().prefetch_related(
                "attributes", "related_products__images", "related_products__variants", "related_products__category"
            ),
            slug=slug,
        )
        return Response(ProductDetailSerializer(product, context={"now": timezone.now(), "request": request}).data)
