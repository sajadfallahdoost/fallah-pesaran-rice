#!/bin/sh
set -eu

case "${1:-web}" in
  web)
    python manage.py migrate --noinput
    python manage.py createcachetable
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-3}" \
      --timeout "${GUNICORN_TIMEOUT:-60}" \
      --access-logfile - \
      --no-control-socket \
      --forwarded-allow-ips "*"
    ;;
  scheduler)
    # Reconcile unfinished payments and expire unpaid orders every 5 minutes.
    while true; do
      python manage.py maintain_orders || echo "maintain_orders failed; retrying in 5 minutes" >&2
      sleep 300
    done
    ;;
  *)
    exec "$@"
    ;;
esac
