from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LuciConfig(AppConfig):
    name = "openwisp_luci"
    label = "openwisp_luci"
    verbose_name = _("LuCI")
