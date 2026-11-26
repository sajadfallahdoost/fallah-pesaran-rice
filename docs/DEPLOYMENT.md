# Deployment

Server deployment uses `/opt/fallah-pesaran-rice` on `213.176.21.32`, with the public
origin `http://213.176.21.32:8090`. The separate project in `/opt/ramtinchem` uses port 80.
Run Compose commands only from the Fallah directory; leave that existing project untouched.

This direct HTTP deployment sets `HTTP_BIND_ADDRESS=0.0.0.0`, `HTTP_PORT=8090`,
`DJANGO_NUM_PROXIES=1`, `DJANGO_SESSION_COOKIE_SECURE=false`, and
`DJANGO_CSRF_COOKIE_SECURE=false`. Configure a domain and HTTPS before real sales, then
remove the two cookie overrides, switch the public origin and CSRF origins to HTTPS,
and rebuild the frontend. The server uses one gunicorn worker to fit its available memory.
Payment credentials must be configured before enabling payments.

Initial data was loaded with `seed_store --no-samples`: categories, shipping, pages and
FAQs are available, but the product catalog starts empty. An administrator account was
created and `sales_enabled` is false until the owner adds real products and configures
SMS and payments. The provided SMS configuration contains a placeholder API key.

The server's `compose.override.yaml` limits resources for this stack and sets its new
network's MTU to 1400. Its session cookie is named `fallah_sessionid` via
`DJANGO_SESSION_COOKIE_NAME` so the two sites do not share login sessions on the same IP.
If building on this server, use `DOCKER_BUILDKIT=0 docker build --network=host` with
`--memory=600m --memory-swap=1500m --cpu-period=100000 --cpu-quota=50000` for the
frontend, and `--memory=512m --memory-swap=1200m` with the same CPU limits for the
backend. Build the images sequentially, using the image names in `compose.yaml`.

## Stack (`compose.yaml`)

| Service | Image | Role |
|---|---|---|
| `db` | `postgres:17-alpine` | Database, volume `pgdata` |
| `backend` | `backend/Dockerfile` | Runs migrations and `createcachetable`, then gunicorn on :8000; healthcheck `/api/health/` |
| `scheduler` | same image | `maintain_orders` every 5 minutes |
| `frontend` | `frontend/Dockerfile` | Next.js standalone server on :3000 |
| `nginx` | `nginx:1.27-alpine` | The only published port, `${HTTP_BIND_ADDRESS:-127.0.0.1}:${HTTP_PORT:-8090}`; routes Django paths, serves `/media/` from the `media` volume, blocks `/api/revalidate` from outside |

Compose project name `fallah-pesaran`: containers, network and volumes are namespaced and do not
touch other projects on the same host. Nothing binds 80/443 directly.

## First deployment

```bash
git clone git@github.com:sajadfallahdoost/fallah-pesaran-rice.git && cd fallah-pesaran-rice
cp .env.production.example .env.production && chmod 600 .env.production
# Fill: PUBLIC_BASE_URL, DJANGO_ALLOWED_HOSTS (keep "backend"), DJANGO_CSRF_TRUSTED_ORIGINS,
# DJANGO_SECRET_KEY, POSTGRES_PASSWORD, STOREFRONT_REVALIDATE_SECRET, SMS and payment credentials.
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # for each secret
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production exec backend python manage.py seed_store --no-samples
docker compose --env-file .env.production exec backend python manage.py createsuperuser
```

`seed_store --no-samples` creates categories, provinces, shipping methods/zones/rates, payment
provider rows (disabled), content pages and FAQs, but **no products**. In production it refuses to
run without `--no-samples`. Content pages are created with "needs owner review" set; review them
before launch.

Production settings refuse to start when `DEBUG` is on, `DJANGO_SECRET_KEY` is missing, the mock
gateway is enabled, or the console SMS backend is selected.

## HTTPS

TLS terminates in front of nginx (a host-level Caddy/nginx/Traefik, or a CDN). Requirements:

- Forward to `127.0.0.1:8090`, pass `Host`, and set `X-Forwarded-Proto: https` and
  `X-Forwarded-For`.
- `DJANGO_NUM_PROXIES=2` (TLS proxy + nginx) so throttling uses the real client IP.
- Session/CSRF cookies are `Secure` in production. After HTTPS works everywhere, raise
  `DJANGO_HSTS_SECONDS` (e.g. 31536000).
- Example Caddyfile: `fallah-rice.ir { reverse_proxy 127.0.0.1:8090 }`.
- Choose one canonical host (`fallah-rice.ir` or `www.fallah-rice.ir`) and redirect the other
  permanently before submitting the Search Console sitemap. Rebuild the frontend after
  `PUBLIC_BASE_URL` points at the final HTTPS origin so canonicals, Open Graph and sitemap
  do not keep localhost or the server IP.

## Updating

```bash
git pull
docker compose --env-file .env.production up -d --build   # migrations run on backend start
```

`NEXT_PUBLIC_SITE_URL` is baked into the storefront image from `PUBLIC_BASE_URL`; rebuild after
changing the domain.

## Backups

Data that matters: the `pgdata` database and the `media` volume (product photos, banners).
Receipts are generated on demand from the database. Secrets live only in `.env.production`; keep a
copy in a password manager, not in backups shared with others.

```bash
# Database (daily via cron; keep off-server copies)
docker compose --env-file .env.production exec -T db \
  pg_dump -U fallah -d fallah -Fc > backups/fallah-$(date +%F).dump
# Media
docker run --rm -v fallah-pesaran_media:/data:ro -v "$PWD/backups":/out alpine \
  tar czf /out/media-$(date +%F).tgz -C /data .
```

Backup files contain customer names, phones and addresses: store them encrypted, restrict access,
and delete old ones on a schedule. Never commit them (`*.dump`, `*.sql` are git-ignored).

## Restore

```bash
docker compose --env-file .env.production stop backend scheduler frontend
docker compose --env-file .env.production exec -T db \
  pg_restore -U fallah -d fallah --clean --if-exists < backups/fallah-YYYY-MM-DD.dump
docker run --rm -v fallah-pesaran_media:/data -v "$PWD/backups":/in alpine \
  sh -c "cd /data && tar xzf /in/media-YYYY-MM-DD.tgz"
docker compose --env-file .env.production up -d
```

Test a restore on a separate machine before relying on the backups.

## Maintenance

- **Logs:** `docker compose --env-file .env.production logs -f backend scheduler`. Merchant
  credentials are redacted from logs.
- **Scheduler:** check it prints `maintain_orders: reconciled=… expired=…` every 5 minutes.
- **Admin dashboard:** the "needs review" card lists orders that need a human (payment mismatch,
  duplicate payment, late payment without stock).
- **Upgrades:** pin versions in `requirements.txt` / `package-lock.json`; run CI before deploying.
- **Disk:** watch the `media` volume and old backups.
