# Deployment

Server deployment uses `/opt/fallah-pesaran-rice` on `213.176.21.32`, with the canonical
origin `https://www.fallah-rice.ir`. Caddy owns ports 80 and 443, redirects HTTP to HTTPS,
and redirects the apex domain to `www`, preserving paths and query strings.
The former Ramtinchem stack is retired; its files, database and media are archived under
`/root/deployment-backups/`. `/root/fallah-release-backup-path` identifies the transition backup.

Production settings use `PUBLIC_BASE_URL=https://www.fallah-rice.ir`,
`DJANGO_ALLOWED_HOSTS=www.fallah-rice.ir,fallah-rice.ir,213.176.21.32,127.0.0.1,localhost,backend`,
and `DJANGO_CSRF_TRUSTED_ORIGINS=https://www.fallah-rice.ir,https://fallah-rice.ir`.
`HTTP_BIND_ADDRESS=127.0.0.1` and `HTTP_PORT=8090` keep nginx's diagnostic listener private.
`DJANGO_NUM_PROXIES=2`, secure session and CSRF cookies, and one gunicorn worker are enabled.
The frontend must be rebuilt whenever the public origin changes.

The production database owns the published catalog, inventory, sales switch, shipping,
payment settings, pages and FAQs. On 2026-11-27 the public API reported sales enabled
and three published products. Check the current settings before release and preserve them
during updates. The existing sample media for tea and olive oil is flagged in the public
catalog.

The server's `compose.override.yaml` limits resources for this stack and sets its new
network's MTU to 1400. Its session cookie is named `fallah_sessionid` via
`DJANGO_SESSION_COOKIE_NAME`. The Compose network lets the frontend build access the
running backend without publishing its port.

Use `sh tools/compose-production.sh` for production operations: it combines `compose.yaml`,
the server's resource overrides, and `compose.https.yaml`. The proxy's `caddy_data` and
`caddy_config` volumes persist certificates and configuration across container replacement.

## Stack (`compose.yaml`)

| Service | Image | Role |
|---|---|---|
| `db` | `postgres:17-alpine` | Database, volume `pgdata` |
| `backend` | `backend/Dockerfile` | Runs migrations and `createcachetable`, then gunicorn on :8000; healthcheck `/api/health/` |
| `scheduler` | same image | `maintain_orders` every 5 minutes |
| `frontend` | `frontend/Dockerfile` | Next.js standalone server on :3000 |
| `nginx` | `nginx:1.27-alpine` | Diagnostic port `${HTTP_BIND_ADDRESS:-127.0.0.1}:${HTTP_PORT:-8090}`; routes Django paths, serves `/media/` from the `media` volume, blocks `/api/revalidate` from outside |
| `proxy` | `caddy:2-alpine` | Added by `compose.https.yaml`; public HTTP/HTTPS, certificates and canonical-host redirects; forwards to nginx over the private Compose network |

Compose project name `fallah-pesaran`: containers, network and volumes are namespaced and do not
touch other projects on the same host. The HTTPS overlay publishes 80/443 through Caddy.

## First deployment

```bash
git clone git@github.com:sajadfallahdoost/fallah-pesaran-rice.git && cd fallah-pesaran-rice
cp .env.production.example .env.production && chmod 600 .env.production
# Fill: PUBLIC_BASE_URL, DJANGO_ALLOWED_HOSTS (keep "backend"), DJANGO_CSRF_TRUSTED_ORIGINS,
# DJANGO_SECRET_KEY, POSTGRES_PASSWORD, STOREFRONT_REVALIDATE_SECRET, SMS and payment credentials.
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # for each secret
```

Set `release="$(git rev-parse HEAD)"` and run the backend image build command from
[Updating](#updating). Start the database and backend to create the Compose network
before running the frontend image build command from the same section.

```sh
sh tools/compose-production.sh up -d --no-build --wait --wait-timeout 240 db backend scheduler
# Run the frontend image build before starting the full stack.
sh tools/compose-production.sh up -d --no-build --wait --wait-timeout 240
sh tools/compose-production.sh exec backend python manage.py seed_store --no-samples
sh tools/compose-production.sh exec backend python manage.py createsuperuser
```

`seed_store --no-samples` creates categories, provinces, shipping methods/zones/rates, payment
provider rows (disabled), content pages and FAQs, but **no products**. In production it refuses to
run without `--no-samples`. Content pages are created with "needs owner review" set; review them
before launch.

Production settings refuse to start when `DEBUG` is on, `DJANGO_SECRET_KEY` is missing, the mock
gateway is enabled, or the console SMS backend is selected.

## Updating

On the server confirm the running image IDs, current checkout and production health first.
Keep the host's `compose.override.yaml` and `.env.production` in place. If a previous
deployment left local tracked changes or colliding untracked files, compare them with
`origin/main` and make a private recovery copy before advancing the checkout. Confirm
there is a recent database and media backup. Review any pending migrations and their
compatibility with the currently running release before the backend starts them.

Run from `/opt/fallah-pesaran-rice` once the checkout is ready to advance. The tag for
each running image preserves an image rollback point while rebuilding its normal tag.
The old backend can serve the frontend build when its API is compatible. If a frontend
build needs a new API from the same release, verify release ordering and migration
compatibility in a separate environment before replacing the running services.

```sh
set -eu
git fetch origin main
test "$(git branch --show-current)" = main
test -z "$(git status --porcelain --untracked-files=no)"
git merge --ff-only origin/main
release="$(git rev-parse HEAD)"
test "$release" = "$(git rev-parse origin/main)"

rollback_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
for service in backend frontend; do
  container_id="$(sh tools/compose-production.sh ps -q "$service")"
  image_id="$(docker inspect --format '{{.Image}}' "$container_id")"
  docker tag "$image_id" "fallah-pesaran/$service:rollback-$rollback_stamp"
done

DOCKER_BUILDKIT=0 docker build --network=host --memory=512m --memory-swap=1200m \
  --cpu-period=100000 --cpu-quota=50000 --build-arg RELEASE_REVISION="$release" \
  -t fallah-pesaran/backend:local backend
DOCKER_BUILDKIT=0 docker build --network=fallah-pesaran_default --memory=600m --memory-swap=1500m \
  --cpu-period=100000 --cpu-quota=50000 --build-arg RELEASE_REVISION="$release" \
  --build-arg BACKEND_INTERNAL_URL=http://backend:8000 \
  --build-arg NEXT_PUBLIC_SITE_URL=https://www.fallah-rice.ir \
  -t fallah-pesaran/frontend:local frontend
sh tools/compose-production.sh up -d --no-build --wait --wait-timeout 240
```

`NEXT_PUBLIC_SITE_URL` is baked into the storefront image. Supply the canonical HTTPS
origin from `PUBLIC_BASE_URL` when building. A release build records `RELEASE_REVISION`
as the OCI revision label on both images and as the Next.js build ID. Builds for local
development and CI can omit this argument.

Run the checks against the containers that are currently serving. A mutable image tag
or the server's checkout alone does not identify an already running container.

```sh
for service in backend scheduler frontend; do
  container_id="$(sh tools/compose-production.sh ps -q "$service")"
  image_id="$(docker inspect --format '{{.Image}}' "$container_id")"
  active_release="$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image_id")"
  test "$active_release" = "$release"
  printf '%s %s %s\n' "$service" "$active_release" "$image_id"
done
test "$(sh tools/compose-production.sh exec -T frontend cat /app/.next/BUILD_ID)" = "$release"
live_release="$(curl -fsS -D - -o /dev/null https://www.fallah-rice.ir/ |
  awk 'tolower($1) == "x-fallah-release:" { sub(/\r$/, "", $2); print $2 }')"
test "$live_release" = "$release"
curl -fsS https://www.fallah-rice.ir/api/health/
```

Check the public sitemap, robots, home, categories, published products, article list,
articles and their images after release. Verify the cart and the checkout screen
through a dedicated test environment or a session without submitting an order or
payment. Product, price, stock and payment data remain managed by the production
database. Run `seed_store` only during initial setup.

If the application fails and the database is still compatible with the old backend,
retag the saved backend and frontend images as their respective `:local` tags and
repeat `up -d --no-build --wait`. If the database schema is incompatible with the
old backend, follow the migration-specific recovery plan before restarting it.

## Backups

Data that matters: the `pgdata` database and the `media` volume (product photos, banners).
Receipts are generated on demand from the database. Secrets live only in `.env.production`; keep a
copy in a password manager, not in backups shared with others.

```bash
# Database and media. Keep encrypted off-server copies.
set -eu
umask 077
backup_dir="/root/deployment-backups/fallah-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$backup_dir"
sh tools/compose-production.sh exec -T db \
  pg_dump -U fallah -d fallah -Fc > "$backup_dir/db.dump"
sh tools/compose-production.sh exec -T db \
  pg_restore --list < "$backup_dir/db.dump" > /dev/null
docker run --rm -v fallah-pesaran_media:/data:ro -v "$backup_dir":/out alpine \
  sh -c 'umask 077; tar czf /out/media.tgz -C /data .'
tar tzf "$backup_dir/media.tgz" > /dev/null
```

Backup files contain customer names, phones and addresses: store them encrypted, restrict access,
and delete old ones on a schedule. Never commit them (`*.dump`, `*.sql` are git-ignored).

## Restore

```bash
backup_dir=/root/deployment-backups/fallah-YYYYMMDDTHHMMSSZ
sh tools/compose-production.sh stop backend scheduler frontend
sh tools/compose-production.sh exec -T db \
  pg_restore -U fallah -d fallah --clean --if-exists < "$backup_dir/db.dump"
docker run --rm -v fallah-pesaran_media:/data -v "$backup_dir":/in:ro alpine \
  tar xzf /in/media.tgz -C /data
sh tools/compose-production.sh up -d --no-build --wait --wait-timeout 240
```

Test a restore on a separate machine before relying on the backups.

## Maintenance

- **Logs:** `sh tools/compose-production.sh logs -f backend scheduler`. Merchant
  credentials are redacted from logs.
- **Scheduler:** check it prints `maintain_orders: reconciled=… expired=…` every 5 minutes.
- **Admin dashboard:** the "needs review" card lists orders that need a human (payment mismatch,
  duplicate payment, late payment without stock).
- **Upgrades:** pin versions in `requirements.txt` / `package-lock.json`; run CI before deploying.
- **Disk:** watch the `media` volume and old backups.
