# Requirements

## Scope

A Persian, right-to-left online store for «فلاح و پسران». Rice is the main category; tea and olive
oil are secondary. Customers in Iran buy packaged goods, pay online through an Iranian bank
gateway (Shaparak), and receive them by post, Tehran courier or freight. One owner (plus optional
staff) runs the store from a Persian admin panel.

Out of scope for this version: marketplace/multi-vendor, wallet or store credit, cash on delivery
(freight is "pay the carrier on delivery" for shipping only), discount codes, product reviews,
blog, B2B ordering, multiple languages, native apps.

Confirmed business data (from the owner): name, address «تهران، میرداماد، میدان مادر», phone
09122122187, email fallahdoostsajad@gmail.com, Telegram @Sajadfallahdoost. Everything else
(history, hours, policies, prices, tariffs) is unconfirmed and shown as draft or omitted.

## Customer journeys

1. **Discover:** home → category or search → product with package sizes, price per package and
   per kilo/litre, stock, delivery information.
2. **Buy as guest:** add to cart → checkout (name, mobile, province, city, address) → choose a
   shipping method with its cost → choose gateway → pay on the bank page → result page with order
   number and receipt.
3. **Retry:** a failed or canceled payment can be retried on the same order until its reservation
   ends; the customer is never charged twice for one order.
4. **Track:** order number + mobile → status, items, shipment tracking.
5. **Account (optional):** mobile + SMS code → order history, saved addresses, faster checkout.
6. **Get help:** FAQ, shipping/returns/privacy/terms pages, contact by phone, Telegram or email.

## Owner journeys

1. Add or edit products, package variants, prices, sale prices with dates, stock, images,
   attributes and descriptions; publish or hide.
2. Configure shipping methods, zones and weight-based rates; store settings and the sales switch.
3. See new paid orders, move them through preparing → shipped (carrier, tracking code) →
   delivered; cancel with a reason; print or download the receipt.
4. Record refunds (partial or full, optional restock) and complete them with the bank reference.
5. Read sales, payment, refund and stock reports for any date range; export CSV.
6. Handle orders flagged "needs review".

## Acceptance checklist

| Requirement | State |
|---|---|
| RTL Persian storefront, responsive 320–1920 px, accessible basics | Done, audited |
| Brand assets (logo variants, icons, usage guide) | Done |
| Original generated imagery integrated and labelled | Done (samples) |
| Catalog with variants, unit price, sale windows, stock, search/filter/sort | Done |
| Server-side cart and pricing, checkout with idempotency and price-change protection | Done, tested |
| Shipping methods/zones/weight rates with eligibility | Done; real tariffs needed |
| Payment via `az-iranian-bank-gateways` behind a service, mock adapter for development | Done; no live provider tested |
| Verification, amount checks, idempotent application, reconciliation job | Done, tested |
| No "mark paid" shortcut; no card data collected | Done, tested |
| Stock reservation, commit, release, no overselling | Done, tested |
| Order lifecycle, events, customer-visible timeline | Done |
| PDF receipt (Persian, Jalali) | Done |
| Refunds with audit trail | Done (manual execution at provider) |
| Reports + CSV (formula-injection safe) | Done, tested |
| Staff roles (owner, order operator, catalog editor) | Done, tested |
| SMS login | Done; real SMS provider needed |
| SEO: metadata, Open Graph, JSON-LD, sitemap, robots | Done |
| Docker Compose, CI, docs, owner guide | Done |
| Deployed on a real domain with HTTPS | Not done: no hosting access |
| Live payment test | Not done: no merchant credentials |

Launch blockers are listed in [TESTING.md](TESTING.md#launch-blockers).
