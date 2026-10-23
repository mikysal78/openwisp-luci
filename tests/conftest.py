import sys
import types

import django
from django.conf import settings


def pytest_configure():
    settings.configure(
        SECRET_KEY="test-only",
        ALLOWED_HOSTS=[".luci.example.com", "openwisp.example.com"],
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
        DATABASES={},
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "APP_DIRS": False,
                "DIRS": ["openwisp_luci/templates"],
            }
        ],
        ROOT_URLCONF="tests.urls",
        USE_TZ=True,
        OPENWISP_LUCI_HOST="{id}.luci.example.com",
    )
    django.setup()
    # permissions.py carica il modello Device di openwisp-controller (GDAL,
    # database): nei test lo sostituisce un modulo finto, vedi test_views.py
    fake = types.ModuleType("openwisp_luci.permissions")
    fake.Device = None
    fake.can_open = None
    fake.device_upstream = None
    sys.modules["openwisp_luci.permissions"] = fake
