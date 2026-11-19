"""Best-effort on-demand revalidation of the Next.js storefront cache after owner edits."""

import logging
import threading

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


def _post(tags: list[str]) -> None:
    try:
        requests.post(
            settings.STOREFRONT_REVALIDATE_URL,
            json={"tags": tags},
            headers={"x-revalidate-secret": settings.STOREFRONT_REVALIDATE_SECRET},
            timeout=3,
        )
    except requests.RequestException:
        logger.info("Storefront revalidation skipped (storefront unreachable).")


def revalidate(*tags: str) -> None:
    if settings.STORE_ENV == "test":
        return
    transaction.on_commit(lambda: threading.Thread(target=_post, args=(list(tags),), daemon=True).start())


def catalog_changed(sender, **kwargs) -> None:
    revalidate("catalog", "site")


def content_changed(sender, **kwargs) -> None:
    revalidate("site", "content", "catalog")
