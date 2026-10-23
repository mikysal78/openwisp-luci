"""Controlla che il wheel contenga tutti i file necessari a runtime."""

import sys
import zipfile

REQUIRED = [
    "openwisp_luci/admin.py",
    "openwisp_luci/views.py",
    "openwisp_luci/urls.py",
    "openwisp_luci/locale/it/LC_MESSAGES/django.mo",
    "openwisp_luci/templates/admin/openwisp_luci/device/change_form.html",
    "openwisp_luci/templates/openwisp_luci/denied.html",
]

names = set(zipfile.ZipFile(sys.argv[1]).namelist())
missing = [name for name in REQUIRED if name not in names]
if missing:
    sys.exit("missing from the wheel: " + ", ".join(missing))
print("wheel ok: %d files" % len(names))
