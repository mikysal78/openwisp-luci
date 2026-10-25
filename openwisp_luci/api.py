"""API per le app (per esempio openwisp-android): link monouso verso LuCI.

    POST /api/v1/luci/device/<uuid>/link/
    Authorization: Bearer <token di openwisp-users>
    -> 200 {"url": "https://<host del device>/__openwisp_luci__/login/?token=..."}

Gli stessi controlli del pulsante nell'admin (can_open: utente staff attivo,
superuser o manager dell'organizzazione del device con il permesso di
modificarlo; IP di gestione ammesso). Il link che ne esce e' quello del
pulsante: monouso, valido TOKEN_AGE secondi, legato a utente, device e
password dell'utente.

Si accetta solo il token Bearer, mai la sessione del browser: per questo la
vista puo' stare fuori dalla protezione CSRF. Un device che l'utente non puo'
aprire risponde 404 come uno che non esiste.
"""

import logging

from django.http import JsonResponse
from django.urls import NoReverseMatch, reverse
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import access
from . import settings as app_settings
from .permissions import Device, can_open, device_upstream

logger = logging.getLogger(__name__)

MAX_TOKEN_LENGTH = 128


def login_path():
    try:
        return reverse("openwisp_luci:login")
    except NoReverseMatch:
        return "/__openwisp_luci__/login/"


def _token_model():
    from rest_framework.authtoken.models import Token

    return Token


def token_user(request):
    """Utente attivo del token Bearer (lo stesso di openwisp-users), o None."""
    kind, _, key = request.META.get("HTTP_AUTHORIZATION", "").partition(" ")
    key = key.strip()
    if kind.lower() != "bearer" or not key or len(key) > MAX_TOKEN_LENGTH:
        return None
    Token = _token_model()
    try:
        user = Token.objects.select_related("user").get(key=key).user
    except Token.DoesNotExist:
        return None
    return user if user.is_active else None


def _error(status, detail):
    response = JsonResponse({"detail": detail}, status=status)
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@never_cache
@require_POST
def link(request, pk):
    user = token_user(request)
    if user is None:
        return _error(401, "Invalid or missing token.")
    if not app_settings.HOST:
        return _error(404, "LuCI proxy disabled.")
    try:
        device = Device.objects.select_related("organization").get(pk=pk)
    except Device.DoesNotExist:
        return _error(404, "Not found.")
    if not can_open(user, device):
        return _error(404, "Not found.")
    if device_upstream(device) is None:
        return _error(409, "The management IP of this device is missing or not allowed.")
    token = access.make_token(user.pk, device.pk, access.user_fingerprint(user))
    host = access.device_host(app_settings.HOST, device.pk)
    logger.info("link LuCI per %s (%s) dato a %s via API", device.name, device.pk, user.username)
    response = JsonResponse({"url": "https://%s%s?%s" % (host, login_path(), urlencode({"token": token}))})
    response["Cache-Control"] = "no-store"
    return response
