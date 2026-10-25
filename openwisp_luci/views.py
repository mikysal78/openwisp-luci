"""Viste servite sull'host del proxy (<id>.luci.example.com).

login: consuma il link monouso arrivato da OpenWISP e lascia il cookie.
auth: chiamata da nginx (auth_request) a ogni richiesta verso il router; con
      204 dice a nginx l'IP del router, con 401 lo ferma.
denied: pagina mostrata da nginx quando auth risponde 401.

Ogni controllo si ripete a ogni richiesta: utente ancora attivo e con il
permesso, password non cambiata, device ancora esistente e con un IP di
gestione ammesso, cookie arrivato proprio sull'host di quel device.
"""

import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from django.http.request import split_domain_port
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from . import access, autologin
from . import settings as app_settings
from .permissions import Device, can_open, device_upstream

logger = logging.getLogger(__name__)


def _host(request):
    return split_domain_port(request.get_host())[0]


def _check(request, data):
    """Utente, device e IP del router se il token o il cookie valgono qui."""
    if data is None:
        return None
    device_hex = access.host_device_id(app_settings.HOST, _host(request))
    if device_hex is None or device_hex != data["d"]:
        return None
    try:
        user = get_user_model().objects.get(pk=data["u"])
        device = Device.objects.select_related("organization").get(pk=uuid.UUID(hex=device_hex))
    except (get_user_model().DoesNotExist, Device.DoesNotExist, ValueError, TypeError):
        return None
    if not access.same_fingerprint(access.user_fingerprint(user), data["f"]):
        return None
    if not can_open(user, device):
        return None
    target = device_upstream(device)
    if target is None:
        return None
    return user, device, target


# Pagina che entra in LuCI dopo il login. Non un redirect 302: quando il link
# arriva da fuori (un'app, un altro sito) il browser considera cross-site anche
# il redirect e non manda i cookie SameSite=Strict appena impostati, quindi
# LuCI aprirebbe "sessione assente". Il meta refresh e' una navigazione che
# parte da questa pagina, sullo stesso host: i cookie Strict arrivano.
ENTER_LUCI = (
    '<!doctype html><html><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    '<meta http-equiv="refresh" content="0;url=/cgi-bin/luci/">'
    "<title>LuCI</title></head>"
    '<body><p><a href="/cgi-bin/luci/">LuCI</a></p></body></html>'
)


def _private(response):
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@never_cache
@require_GET
def login(request):
    data = access.read_token(request.GET.get("token", ""), app_settings.TOKEN_AGE)
    checked = _check(request, data)
    # monouso: il nonce si brucia solo se tutto il resto e' valido
    if checked is None or not cache.add(access.nonce_key(data["n"]), 1, app_settings.TOKEN_AGE + 60):
        return _private(denied(request, status=403))
    user, device, target = checked
    response = HttpResponse(ENTER_LUCI)
    response["Content-Security-Policy"] = "default-src 'none'"
    # accesso automatico solo per i superuser; gli altri usano la password
    sid = autologin.router_session(device) if getattr(user, "is_superuser", False) else None
    if sid:
        response.set_cookie(
            autologin.COOKIE_NAME,
            sid,
            path=autologin.COOKIE_PATH,
            secure=True,
            httponly=True,
            samesite="Strict",
        )
    logger.info(
        "LuCI di %s (%s) aperta da %s verso %s%s",
        device.name,
        device.pk,
        user.username,
        target,
        " con accesso automatico come %s" % app_settings.AUTO_LOGIN_USER if sid else "",
    )
    response.set_cookie(
        access.COOKIE_NAME,
        access.make_cookie(user.pk, data["d"], data["f"]),
        max_age=app_settings.SESSION_AGE,
        path="/",
        secure=True,
        httponly=True,
        samesite="Strict",
    )
    return _private(response)


@csrf_exempt
@never_cache
def auth(request):
    # niente @require_GET: nginx usa il metodo della richiesta originale (anche
    # POST per il login di LuCI), ma qui non si legge mai il corpo
    data = access.read_cookie(request.COOKIES.get(access.COOKIE_NAME, ""), app_settings.SESSION_AGE)
    checked = _check(request, data)
    if checked is None:
        return HttpResponse(status=401)
    response = HttpResponse(status=204)
    response[access.UPSTREAM_HEADER] = checked[2]
    return response


@csrf_exempt
@never_cache
def denied(request, status=403):
    device_url = None
    device_hex = access.host_device_id(app_settings.HOST, _host(request))
    if app_settings.OPENWISP_URL and device_hex:
        info = Device._meta.app_label, Device._meta.model_name
        path = reverse("admin:%s_%s_change" % info, args=[str(uuid.UUID(hex=device_hex))])
        device_url = app_settings.OPENWISP_URL.rstrip("/") + path
    response = render(
        request,
        "openwisp_luci/denied.html",
        {"device_url": device_url, "title": _("LuCI session missing or expired")},
        status=status,
    )
    return _private(response)
