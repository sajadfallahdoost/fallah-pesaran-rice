# Payments

**Readiness: development-ready only.** The complete flow is implemented and tested end to end with a
development mock bank that runs through the real library lifecycle. **No real gateway has been
contacted and no live or sandbox transaction has been run**, because no merchant credentials were
provided. Real money cannot be accepted until the steps in [Going live](#going-live) are done.

## Library

- [`az-iranian-bank-gateways`](https://github.com/ali-zahedi/az-iranian-bank-gateways) **2.3.4**
  (released 2026-01-07), MIT license (notice in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)).
- Compatible with Django 5.2.19 / Python 3.12 (checked: `check`, migrations, full flow).
- Detailed source review, pitfalls and test results: [PAYMENT_LIBRARY_NOTES.md](PAYMENT_LIBRARY_NOTES.md).
- Wrapped by `backend/apps/payments/services.py`; views and the storefront never call it directly.

## Providers

A provider is offered at checkout only when **both** its credentials are set in the server
environment **and** it is enabled in the admin (پرداخت › درگاه‌های پرداخت). Seeded rows:

| Code | Name | Environment variables | Notes |
|---|---|---|---|
| `ZARINPAL` | زرین‌پال | `ZARINPAL_MERCHANT_CODE`, `ZARINPAL_SANDBOX` | REST v4, integer rial, with a sandbox. |
| `ZIBAL` | زیبال | `ZIBAL_MERCHANT_CODE` | Merchant `zibal` is Zibal's public test merchant. |
| `SEP` | سامان (سپ) | `SEP_MERCHANT_CODE`, `SEP_TERMINAL_CODE` | POST redirect form. |
| `MELLAT` | ملت (به‌پرداخت) | `MELLAT_TERMINAL_CODE`, `MELLAT_USERNAME`, `MELLAT_PASSWORD` | SOAP; POST callback. |
| `BMI` | ملی (سداد) | `BMI_MERCHANT_CODE`, `BMI_TERMINAL_CODE`, `BMI_SECRET_KEY` | POST callback. |
| `MOCK` | درگاه آزمایشی | `PAYMENT_MOCK_ENABLED=true` | Development only; settings refuse to start in production with it enabled, and its page returns 404 when disabled. |

`PAYMENT_DEFAULT_PROVIDER` picks the library default. Secrets live only in server environment
variables, are never sent to the browser, and a logging filter redacts them because the library
logs request payloads (including merchant ids) on gateway errors.

## Units

The storefront displays toman. Orders retain the server-calculated integer rial amount. Both the
Zarinpal REST v4 request and its verification use that same rial amount. The payment request sends
`currency="IRR"` explicitly. The adapter preserves the previous minimum of 1,000 toman.

## Flow

1. **Checkout** creates the order (`awaiting_payment`, stock reserved for 30 minutes).
2. **Start payment** `POST /api/v1/orders/<number>/pay/` with the order token and provider:
   - Locks the order; refuses if already paid, expired, canceled or past its reservation.
   - Resolves earlier attempts first. A previous attempt still **unknown** blocks a new one
     (`previous_payment_pending`) so a customer is never charged twice while a result is pending;
     an attempt the customer abandoned at the gateway does not block a retry.
   - Creates a `PaymentAttempt` (amount = order total), then the library `ready()` +
     `get_gateway()` in the same request (the library's 120-second window). The initiating query
     string is stripped so the order token never reaches a gateway.
   - Returns `{url, method, params}`; the storefront redirects (GET) or auto-submits a form (POST).
3. **Gateway → library callback** `/bankgateways/callback/`: the library verifies with the provider
   and stores the result on its `Bank` row, then redirects to our return URL.
4. **Return** `GET /api/v1/payments/return/?attempt=<id>&tc=<tracking code>`: reads only persisted
   state. The query string can never mark a payment successful. It checks that tracking code,
   provider and **amount** match the attempt; a mismatch marks the attempt `mismatch` and flags
   the order for review instead of confirming it.
5. **Apply** (`orders/services/lifecycle.apply_verified_payment`): locks the order, applies the
   payment exactly once, commits stock, issues the receipt, records events and audit entries.
   Duplicate payments, payments after cancellation and late payments without stock are recorded
   and flagged for review, never silently applied.
6. The customer lands on `/checkout/result/<number>` which shows paid, pending (polls), failed
   (retry with provider choice) or expired.

Attempt statuses: `created`, `redirected`, `succeeded`, `failed`, `canceled`, `unknown`
(returned but verify did not finish), `expired` (abandoned at the gateway for 20+ minutes),
`mismatch`.

## Reconciliation

`manage.py maintain_orders` (scheduler, every 5 minutes) handles attempts 10 minutes to 3 days old:
re-verifies attempts the library left in "returned from bank" (provider timeout during callback),
marks attempts abandoned for 20 minutes as expired, then expires unpaid orders. An order is not
expired while a payment attempt is younger than 20 minutes. The library's own
`update_expire_records()` is not used (it uses naive datetimes). Never call `verify()` on a
completed record: the library would downgrade it on a negative provider reply.

## Refunds

The library has no refund API. Refunds are recorded in the admin and completed only with the bank
reference after the money is returned through the provider's merchant panel or a bank transfer.

## What the tests prove (mock bank, real library code path)

Success confirms once; repeated callbacks are idempotent; a tampered return query cannot mark paid;
amount mismatch flags review; timeout followed by reconciliation applies the payment; expiry
releases stock and a late payment reclaims it or flags review; a second successful payment is
flagged, not applied; a paid order cannot start another payment; the order token never reaches the
gateway; the mock gateway refuses foreign callbacks and is 404 when disabled; Zarinpal receives
integer rial. See [TESTING.md](TESTING.md).

## Going live

1. Sign a merchant contract with at least one provider; register the production domain and
   callback URL `https://<domain>/bankgateways/callback/` with the provider (Zarinpal checks it).
2. Put the credentials in `.env.production` on the server only; restart; enable the provider in
   the admin and disable nothing else by accident.
3. Ensure `PUBLIC_BASE_URL` is the public https origin and the TLS proxy sends
   `X-Forwarded-Proto: https`.
4. With the owner's consent, run one small real payment and a refund through the provider panel;
   confirm the order, receipt, report totals and the refund record. Where a provider offers a
   sandbox (Zarinpal, Zibal test merchant), test there first.
5. Keep `maintain_orders` running and watch the "needs review" card on the admin dashboard.
