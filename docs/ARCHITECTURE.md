# Architecture

A modular monolith: one Django project (API + admin + payment callbacks) and one Next.js storefront,
served from a single public origin so session and CSRF cookies stay first-party.

```
browser ──► nginx ──► Next.js storefront (pages, /media proxy, /api/revalidate)
                 ├──► Django: /api/v1, /api/health, /admin, /bankgateways, /payments, /static
                 └──► /media/ (uploaded images, from the media volume)
Next.js server ──► Django /api/v1 (catalog/site data, cached with tags)
Django ──► Next.js /api/revalidate (after admin edits; shared secret)
scheduler ──► manage.py maintain_orders every 5 minutes
```

In development `next dev` proxies the Django paths itself (`frontend/next.config.ts`), so the browser
only ever talks to `localhost:3010`.

## Backend apps (`backend/apps/`)

| App | Responsibility |
|---|---|
| `core` | Store settings (contacts, sales switch, tax rate), home banners, content pages, FAQs, audit log, admin dashboard, money/date/text helpers, log redaction, staff roles |
| `catalog` | Categories, products, images, attributes, variants (package size, price, sale price/window, stock, shipping weight) |
| `accounts` | Phone + SMS one-time-code login for customers, saved addresses |
| `shipping` | Provinces, zones (provinces and/or named cities), methods, weight-based rates |
| `orders` | Cart, checkout, orders, items, events, shipments, receipts (invoices), refunds; services for pricing, inventory, lifecycle |
| `payments` | Payment providers, payment attempts, the service wrapping `az-iranian-bank-gateways`, the development mock bank |
| `reports` | Sales/payment/refund/stock reports and CSV export, computed from stored verified data |

Staff roles are Django groups kept in sync after every `migrate` (`apps/core/roles.py`):
**مالک فروشگاه** (owner; everything including financial reports and refunds), **اپراتور سفارش**
(order operator; view orders, process fulfillment), **ویرایشگر کاتالوگ** (catalog editor; products,
content, shipping). Customers can never log into the admin, and staff cannot log in with SMS codes.

## Money

- All amounts are stored and sent over the API as **integer Iranian rial** (`BigIntegerField`).
  The storefront and admin display toman (rial ÷ 10) with Persian digits.
- Prices entered in the admin must be whole toman (multiples of 10 rial); a validator enforces it.
- The browser never supplies prices: the server re-prices the cart on every read and at checkout
  (`orders/services/pricing.py`). Checkout also receives the total the customer saw
  (`expected_total`) and refuses with `total_changed` if the server total differs.
- Totals: merchandise subtotal (sale prices applied if inside their window) + shipping + tax
  (store-level basis points, default 0, rounded down to a whole toman).
- The order stores a snapshot of every line (name, package, unit price, weight) so later catalog
  edits never change past orders, receipts or reports.

## Stock

- Checkout locks the variant rows (`SELECT … FOR UPDATE`, in a stable id order) and **reserves**
  stock by decrementing it; the order's `stock_state` is `reserved`.
- A verified payment turns the reservation into `committed`. Expiry (default 30 minutes,
  `ORDER_RESERVATION_MINUTES`) or cancellation **releases** it, exactly once.
- A payment that arrives after release tries to reserve again; if stock is gone the order is
  confirmed but flagged **needs review** (supply the goods or refund).
- A full refund marked "restock" returns committed stock.
- Concurrency tests prove the last unit is sold once and parallel multi-item orders never oversell.

## Order states

`status`: `awaiting_payment` → `confirmed` (verified payment) | `expired` (reservation timed out) |
`canceled` (staff, with a reason; shipped orders cannot be canceled).

`payment_status`: `unpaid` → `paid` → `partially_refunded` / `refunded` (only when a refund is
recorded as completed with a bank reference).

`fulfillment_status` (only after payment): `unfulfilled` → `preparing` → `shipped` →
`delivered`; `shipped`/`delivered` → `returned`. Invalid jumps are rejected.

`needs_review` + `review_reason` flag anything that requires a human: amount/provider mismatch,
duplicate payment, payment after cancellation, late payment without stock, paid order canceled.

Customers see one derived **stage**: `awaiting_payment`, `under_review`, `unfulfilled`,
`preparing`, `shipped`, `delivered`, `returned`, `expired`, `canceled`.

Every transition locks the order row, writes an `OrderEvent` (some visible to the customer) and,
for money-related actions, an `AuditLog` entry.

## Payments

See [PAYMENTS.md](PAYMENTS.md). In short: a `PaymentAttempt` per try; the library verifies at its
callback; our return view copies the verified result, checks tracking code, provider and amount,
then applies it to the order exactly once. There is **no** admin action that marks an order paid.

## Refunds

Staff record a refund request (amount ≤ refundable remainder, whole toman, reason required;
restock only with a full refund) → approve or reject → **completed** only with the external bank
reference after the money was actually returned outside the store. The gateway library has no
refund API, so the store never claims a refund was sent automatically.

## Public API (`/api/v1/`)

All JSON; unsafe methods require the CSRF token (session-cookie authentication). Throttled:
cart 120/min, checkout/pay/track/OTP 10/min per client.

| Endpoint | Purpose |
|---|---|
| `GET site/`, `home/`, `pages/<slug>/`, `faqs/`, `csrf/` | Store info, home content, content pages, FAQs, CSRF cookie |
| `GET categories/`, `categories/<slug>/`, `products/`, `products/<slug>/` | Catalog (published only; filters `q`, `category`, `in_stock`, `featured`, `sort`, pagination) |
| `GET cart/`, `POST cart/items/`, `PATCH/DELETE cart/items/<variant_id>/` | Server-side cart (session or user) |
| `GET shipping/provinces/`, `POST checkout/quote/` | Destinations and shipping options with costs |
| `POST checkout/` | Create the order (idempotency key, expected total) |
| `GET orders/<number>/?t=<token>` | Order view for its owner or the holder of the secret order token |
| `POST orders/<number>/pay/` | Start a payment attempt; returns `{url, method, params}` for the gateway |
| `GET orders/<number>/invoice.pdf?t=` | PDF receipt for paid orders |
| `POST orders/track/` | Tracking by order number + phone (no private data returned) |
| `GET payments/providers/`, `GET payments/return/` | Selectable gateways; callback target after the library's verify |
| `POST auth/otp/request/`, `auth/otp/verify/`, `GET auth/me/`, `POST auth/logout/` | Customer login |
| `GET account/orders/`, `account/orders/<number>/`, `account/addresses/…` | Signed-in customer data |
| `GET /api/health/` | Liveness + database check |

## Storefront (`frontend/src/app/`)

Pages: home, shop, category, product, cart, checkout, payment result, order tracking, account
(login, orders, addresses), about, contact, FAQ, content pages (`/info/<slug>`), 404, error,
`robots.txt`, `sitemap.xml`, web manifest. Catalog/content data are fetched on the server with
cache tags (`site`, `catalog`, `content`, `product:<slug>`) that Django invalidates after edits.
Cart, checkout, payment result and account are client components talking to the API.

`/media/[...path]` is a route handler that proxies uploaded images (to Django in development, to
nginx in production) because Next's image optimizer cannot fetch them through a rewrite.

## Scheduled maintenance

`manage.py maintain_orders` (every 5 minutes): re-verifies attempts stuck between redirect and
verify (via the library), marks abandoned attempts expired, then expires unpaid orders whose
reservation ended (with a grace period for in-flight payments). Reconciliation runs first so a
real payment is applied before its order could expire.
