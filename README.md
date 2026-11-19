# فلاح و پسران — Fallah & Sons store

A Persian (RTL) online store for Iranian rice, with tea and olive oil as secondary categories.
Customers browse, compare package prices per kilo/litre, check out as guests or with an SMS code,
pay through an Iranian bank gateway, and track orders. The owner manages catalog, prices, stock,
shipping, orders, refunds, receipts and sales reports in a Persian Django admin.

> **Status: working demo, not launched.** The catalog contains 3 clearly labelled sample products with
> generated images and fixture prices. Payments run against a development mock gateway. See
> [docs/TESTING.md](docs/TESTING.md#launch-blockers) for what is still needed before real sales.

| Part | Stack |
|---|---|
| `backend/` | Python 3.12, Django 5.2, Django REST Framework, PostgreSQL 17, `az-iranian-bank-gateways` 2.3.4, WeasyPrint (PDF receipts), gunicorn |
| `frontend/` | Next.js 16 (App Router, Cache Components), React 19, TypeScript, Tailwind CSS 4, Vazirmatn font |
| `infra/` | nginx config; `compose.yaml` at the root runs the full stack |
| `docs/` | Requirements, architecture, payments, deployment, testing, design, assets, owner guide (Persian) |

## Prerequisites

- Python 3.12 and system libraries for WeasyPrint (Debian/Ubuntu: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`)
- Node.js 20+
- Docker (for PostgreSQL in development, and for the production-style stack)

## Local development

```bash
# 1. Database (dev only; any free local port works)
docker run -d --name fallah-dev-db -p 127.0.0.1:55432:5432 \
  -e POSTGRES_USER=fallah -e POSTGRES_PASSWORD=fallah_dev_pw -e POSTGRES_DB=fallah postgres:17-alpine

# 2. Backend on :8010
cd backend
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # development defaults; never commit .env
set -a; . ./.env; set +a
python manage.py migrate
python manage.py createcachetable
python manage.py seed_store     # categories, shipping, pages, FAQs, 3 sample products
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8010

# 3. Storefront on :3010 (proxies /api, /admin, /payments … to Django)
cd frontend
npm ci
npm run dev
```

Open http://localhost:3010 for the store and http://localhost:3010/admin/ for the admin.
In development the SMS login code is printed in the Django console, and checkout pays through the
mock gateway, which simulates success, cancel, bank error or timeout without moving money.

Run `python manage.py maintain_orders` periodically (every 5 minutes in production) to reconcile
unfinished payments and expire unpaid orders.

## Common commands

| Task | Command |
|---|---|
| Backend lint / format | `cd backend && ruff check . && ruff format --check .` |
| Backend tests (needs the dev database) | `cd backend && pytest` |
| Migration drift check | `python manage.py makemigrations --check --dry-run` |
| Frontend types / lint / build | `cd frontend && npx next typegen && npm run typecheck && npm run lint && npm run build` |
| Production-style stack | `docker compose --env-file .env.production up -d --build` (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)) |

## Documentation

- [Requirements and acceptance checklist](docs/REQUIREMENTS.md)
- [Architecture: models, APIs, order/payment states, money and stock rules](docs/ARCHITECTURE.md)
- [Payments](docs/PAYMENTS.md) and [library notes](docs/PAYMENT_LIBRARY_NOTES.md)
- [Deployment, HTTPS, backups](docs/DEPLOYMENT.md)
- [Testing results and launch blockers](docs/TESTING.md)
- [Design system](docs/DESIGN_SYSTEM.md), [brand usage](docs/BRAND.md), [image assets](docs/ASSETS.md)
- [Decisions and assumptions](docs/DECISIONS.md)
- [Reference research](docs/REFERENCE_RESEARCH.md)
- [راهنمای فارسی مدیریت فروشگاه](docs/STORE_OWNER_GUIDE_FA.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Contact (as confirmed by the owner)

Tehran, Mirdamad, Madar Square · 09122122187 · fallahdoostsajad@gmail.com · Telegram @Sajadfallahdoost
