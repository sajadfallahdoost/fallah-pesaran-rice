from azbankgateways.urls import az_bank_gateways_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as accounts
from apps.catalog import views as catalog
from apps.core import views as core
from apps.orders import views as orders
from apps.payments import views as payments
from apps.reports import views as reports

api_v1 = [
    path("site/", core.SiteView.as_view()),
    path("home/", core.HomeView.as_view()),
    path("pages/<slug:slug>/", core.PageView.as_view()),
    path("faqs/", core.FaqView.as_view()),
    path("csrf/", core.CsrfView.as_view()),
    path("categories/", catalog.CategoryListView.as_view()),
    path("categories/<slug:slug>/", catalog.CategoryDetailView.as_view()),
    path("products/", catalog.ProductListView.as_view()),
    path("products/<slug:slug>/", catalog.ProductDetailView.as_view()),
    path("cart/", orders.CartView.as_view()),
    path("cart/items/", orders.CartItemsView.as_view()),
    path("cart/items/<int:variant_id>/", orders.CartItemView.as_view()),
    path("shipping/provinces/", orders.ProvinceListView.as_view()),
    path("checkout/quote/", orders.QuoteView.as_view()),
    path("checkout/", orders.CheckoutView.as_view()),
    path("orders/track/", orders.TrackView.as_view()),
    path("orders/<str:number>/", orders.OrderDetailView.as_view()),
    path("orders/<str:number>/pay/", orders.OrderPayView.as_view()),
    path("orders/<str:number>/invoice.pdf", orders.OrderInvoiceView.as_view()),
    path("payments/providers/", payments.ProvidersView.as_view()),
    path("payments/return/", payments.payment_return, name="payment-return"),
    path("auth/otp/request/", accounts.OtpRequestView.as_view()),
    path("auth/otp/verify/", accounts.OtpVerifyView.as_view()),
    path("auth/me/", accounts.MeView.as_view()),
    path("auth/logout/", accounts.LogoutView.as_view()),
    path("account/orders/", orders.AccountOrdersView.as_view()),
    path("account/orders/<str:number>/", orders.AccountOrderDetailView.as_view()),
    path("account/addresses/", accounts.AddressListView.as_view()),
    path("account/addresses/<int:pk>/", accounts.AddressDetailView.as_view()),
]

payments_urls = ([path("mock-gateway/", payments.mock_gateway, name="mock-gateway")], "payments")

urlpatterns = [
    path("admin/reports/", admin.site.admin_view(reports.sales_report), name="sales-report"),
    path("admin/reports/export/<str:kind>.csv", admin.site.admin_view(reports.export_csv), name="sales-report-export"),
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/health/", core.health),
    path("bankgateways/", az_bank_gateways_urls()),
    path("payments/", include(payments_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
