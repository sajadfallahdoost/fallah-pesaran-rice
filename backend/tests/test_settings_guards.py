"""Production must refuse unsafe configuration (evaluated in a fresh interpreter)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
BASE_ENV = {
    "PATH": os.environ.get("PATH", ""),
    "STORE_ENV": "production",
    "DJANGO_SECRET_KEY": "x" * 60,
    "DJANGO_DEBUG": "false",
    "SMS_BACKEND": "kavenegar",
    "KAVENEGAR_API_KEY": "k",
    "KAVENEGAR_OTP_TEMPLATE": "t",
    "DATABASE_URL": "postgres://u:p@127.0.0.1:1/db",
}


def _load(**overrides) -> subprocess.CompletedProcess:
    env = {**BASE_ENV, **overrides}
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import config.settings as s; print(s.PAYMENT_MOCK_ENABLED, 'MOCK' in s.AZ_IRANIAN_BANK_GATEWAYS['GATEWAYS'])",
        ],
        cwd=BACKEND,
        env={k: v for k, v in env.items() if v is not None},
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_defaults_are_safe():
    result = _load()
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False False"


@pytest.mark.parametrize(
    "overrides",
    [
        {"PAYMENT_MOCK_ENABLED": "true"},
        {"DJANGO_DEBUG": "true"},
        {"SMS_BACKEND": "console"},
        {"DJANGO_SECRET_KEY": None},
    ],
)
def test_production_refuses_unsafe_settings(overrides):
    result = _load(**overrides)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
