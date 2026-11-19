# Decisions and assumptions

## Product

1. **Package price first, unit price second.** Each package shows its price and the price per
   kilo or litre, because Iranian rice shoppers compare per kilo but pay per bag
   ([research](REFERENCE_RESEARCH.md)).
2. **One product, several packages.** Sizes are variants with their own SKU, price, stock and
   shipping weight, instead of one product per weight.
3. **Guest checkout by default.** Login is optional and only by SMS code; it adds history and saved
   addresses. Staff accounts cannot use SMS login.
4. **Guest orders are not attached to an account automatically.** Knowing a phone number must not
   reveal someone's orders; guests use the order link or tracking form.
5. **No invented trust content.** No reviews, sales counts, bestseller labels, seals, certificates,
   health claims or company history. Policy pages are drafts flagged for owner review (the site shows a draft notice on them).
6. **Samples are visible as samples.** Three demo products with generated images carry a sample
   badge and a site-wide demo banner; they are excluded from the sitemap and search indexing, cannot
   be bought in production, and orders for them are flagged as test data and excluded from reports.
7. **Freight is "shipping paid on delivery"** (common for heavy rice orders, ≥ 20 kg); goods are
   always paid online.

## Technical

1. **Modular monolith:** one Django project + one Next.js app, one public origin (cookies stay
   first-party, no CORS).
2. **Money as integer rial** everywhere; toman only for display. Whole-toman validation so gateway
   conversion is exact.
3. **Server is the source of truth** for prices, totals, stock and payment status; the client sends
   only ids, quantities and the total it displayed.
4. **Stock is reserved at checkout** (30 minutes) rather than at payment, so a paid order always has
   goods; expiry releases it. Late payments are reconciled, never lost.
5. **Payments through `az-iranian-bank-gateways`**, wrapped by a service. The library verifies at its
   callback; we never re-verify completed records and always compare amount, provider and tracking
   code before applying. `IS_SAFE_GET_GATEWAY_PAYMENT` is on (no open redirect page).
6. **Mock bank as a library bank class**, so development exercises the real lifecycle. It is only
   registered when enabled, and production refuses to start with it.
7. **No refund automation:** the library has none; refunds are recorded and completed with a bank
   reference.
8. **Database cache instead of Redis** for throttling: one fewer service for a small shop.
9. **Scheduler container with a loop** instead of Celery/cron: the only periodic job is
   `maintain_orders` every 5 minutes.
10. **Next.js Cache Components** with tag revalidation from Django: fast cached catalog pages and
    immediate updates after admin edits.
11. **Uploaded media served by nginx**, proxied by a Next route for the image optimizer.
12. **Django admin, customised in Persian,** rather than a custom dashboard: reliable permissions,
    audit and forms with far less code. Dashboard cards and reports are added on top.
13. **Receipts, not tax invoices.** The PDF is a sales receipt; a formal tax invoice (with economic
    code etc.) needs the owner's tax details.

## Assumptions to confirm with the owner

- Prices are in toman and include no VAT (tax rate setting defaults to 0).
- Reservation window of 30 minutes; payment attempts abandoned after 20 minutes.
- Shipping: post nationwide by weight, courier inside Tehran city only, freight for 20 kg and more.
  All amounts are placeholders.
- Delivery estimates, business hours, return window and conditions: not set until the owner decides.
- Brand name «فلاح و پسران» is the owner's to use; fallah.shop trades under a similar name. No
  trademark search was done.
- Kavenegar as SMS provider (common in Iran); any provider can be added in `apps/accounts/sms.py`.
