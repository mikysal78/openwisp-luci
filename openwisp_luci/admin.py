"""Pulsante «LuCI» nella pagina del device.

Estende l'admin del device gia' registrato (openwisp-monitoring,
openwisp-netconsole...) invece di sostituirlo: per questo l'app va messa in
INSTALLED_APPS dopo le app che registrano o estendono quell'admin.

Il pulsante apre la vista open_luci, che passa da admin_site.admin_view (utente
staff autenticato), prende il device con get_object (queryset filtrato per
organizzazione) e richiede il permesso di modificarlo: solo allora firma il
link monouso verso l'host del proxy di quel device.
"""

import logging

from django.contrib import admin, messages
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponseRedirect
from django.urls import NoReverseMatch, path, reverse
from django.utils.http import urlencode
from django.utils.translation import gettext as _

from . import access
from . import settings as app_settings
from .permissions import Device, can_open, device_upstream

logger = logging.getLogger(__name__)

try:
    BaseDeviceAdmin = type(admin.site._registry[Device])
except KeyError as e:
    raise ImproperlyConfigured(
        "openwisp_luci va messo in INSTALLED_APPS dopo openwisp_controller.config "
        "(e dopo openwisp_monitoring.device e openwisp_netconsole, se presenti)"
    ) from e


def _login_path():
    try:
        return reverse("openwisp_luci:login")
    except NoReverseMatch:
        return "/__openwisp_luci__/login/"


class LuciDeviceAdmin(BaseDeviceAdmin):
    change_form_template = "admin/openwisp_luci/device/change_form.html"

    def get_urls(self):
        info = self.opts.app_label, self.opts.model_name
        return [
            path(
                "<uuid:pk>/luci/",
                self.admin_site.admin_view(self.open_luci_view),
                name="%s_%s_luci" % info,
            ),
        ] + super().get_urls()

    def get_extra_context(self, pk=None):
        ctx = super().get_extra_context(pk)
        ctx["luci_parent_template"] = BaseDeviceAdmin.change_form_template
        if pk and app_settings.HOST:
            info = self.opts.app_label, self.opts.model_name
            ctx["luci_url"] = reverse("admin:%s_%s_luci" % info, args=[pk])
        return ctx

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        # qui e non in change_view: il change_view di openwisp-controller
        # ricostruisce extra_context e scarta quello ricevuto
        if obj is not None and app_settings.HOST and can_open(request.user, obj):
            context["luci_allowed"] = True
            if device_upstream(obj) is None:
                context["luci_unavailable"] = _(
                    "LuCI: the management IP of this device is missing or not allowed"
                )
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def open_luci_view(self, request, pk):
        device = self.get_object(request, str(pk))
        if device is None or not app_settings.HOST or not can_open(request.user, device):
            raise Http404
        if not self.has_change_permission(request, device):
            raise Http404
        info = self.opts.app_label, self.opts.model_name
        if device_upstream(device) is None:
            messages.error(request, _("LuCI: the management IP of this device is missing or not allowed"))
            return HttpResponseRedirect(reverse("admin:%s_%s_change" % info, args=[pk]))
        token = access.make_token(request.user.pk, device.pk, access.user_fingerprint(request.user))
        host = access.device_host(app_settings.HOST, device.pk)
        logger.info("link LuCI per %s (%s) dato a %s", device.name, device.pk, request.user.username)
        response = HttpResponseRedirect(
            "https://%s%s?%s" % (host, _login_path(), urlencode({"token": token}))
        )
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


admin.site.unregister(Device)
admin.site.register(Device, LuciDeviceAdmin)
