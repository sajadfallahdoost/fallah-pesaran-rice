FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# WeasyPrint (PDF receipts) needs Pango/HarfBuzz; libpq comes with psycopg[binary].
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --home /app app

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .
RUN chmod +x docker-entrypoint.sh \
    && mkdir -p /data/media /app/staticfiles \
    && chown -R app:app /data /app/staticfiles \
    && STORE_ENV=build DJANGO_DEBUG=false DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

USER app
ENV DJANGO_MEDIA_ROOT=/data/media \
    DJANGO_STATIC_ROOT=/app/staticfiles

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
