"""Link monouso, cookie del proxy e indirizzo del router.

Flusso: la pagina del device in OpenWISP (utente staff con il permesso di
modificare il device) firma un token valido TOKEN_AGE secondi e rimanda il
browser a https://<host del device>/__openwisp_luci__/login/?token=...; la vista
di login lo verifica, lo consuma (monouso) e lascia un cookie firmato legato a
utente, device e password dell'utente. Poi nginx chiede a ogni richiesta, con
auth_request, se il cookie vale ancora e verso quale IP inoltrare.

Qui sta solo la logica senza database, per poterla provare da sola.
"""

import hashlib
import ipaddress
import re
import secrets
import uuid

from django.core import signing
from django.utils.crypto import constant_time_compare, salted_hmac

TOKEN_SALT = "openwisp_luci.token"
COOKIE_SALT = "openwisp_luci.cookie"
FINGERPRINT_SALT = "openwisp_luci.user"
# __Host-: il browser lo accetta solo Secure, con Path=/ e senza Domain, quindi
# nessun altro sottodominio puo' impostarlo o sovrascriverlo
COOKIE_NAME = "__Host-openwisp-luci"
UPSTREAM_HEADER = "X-OpenWISP-LuCI-Upstream"


def device_host(template, device_pk):
    """Host del proxy per il device."""
    if not template or template.count("{id}") != 1:
        return None
    return template.replace("{id}", uuid.UUID(str(device_pk)).hex).lower()


def host_device_id(template, host):
    """UUID (hex) del device dall'host della richiesta, o None."""
    if not template or template.count("{id}") != 1 or not host:
        return None
    before, after = template.lower().split("{id}")
    pattern = "^%s([0-9a-f]{32})%s$" % (re.escape(before), re.escape(after))
    match = re.match(pattern, host.lower().rstrip("."))
    return match.group(1) if match else None


def user_fingerprint(user):
    """Cambia se cambia la password: chiude anche le sessioni LuCI aperte."""
    return salted_hmac(FINGERPRINT_SALT, user.get_session_auth_hash(), algorithm="sha256").hexdigest()[:32]


def make_token(user_pk, device_pk, fingerprint):
    data = {
        "u": str(user_pk),
        "d": uuid.UUID(str(device_pk)).hex,
        "f": fingerprint,
        "n": secrets.token_urlsafe(16),
    }
    return signing.dumps(data, salt=TOKEN_SALT)


def nonce_key(nonce):
    return "openwisp_luci:nonce:%s" % hashlib.sha256(nonce.encode()).hexdigest()


def _load(value, salt, max_age, keys):
    if not value or len(value) > 1024:
        return None
    try:
        data = signing.loads(value, salt=salt, max_age=max_age)
    except signing.BadSignature:
        return None
    if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and data[k] for k in keys):
        return None
    return data


def read_token(token, max_age):
    return _load(token, TOKEN_SALT, max_age, ("u", "d", "f", "n"))


def make_cookie(user_pk, device_hex, fingerprint):
    return signing.dumps({"u": str(user_pk), "d": device_hex, "f": fingerprint}, salt=COOKIE_SALT)


def read_cookie(value, max_age):
    return _load(value, COOKIE_SALT, max_age, ("u", "d", "f"))


def same_fingerprint(a, b):
    return constant_time_compare(a, b)


def upstream(ip, allowed_networks):
    """IP del router nella forma che va in proxy_pass, o None se non ammesso."""
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return None
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_unspecified or addr.is_reserved:
        return None
    for network in allowed_networks:
        try:
            if addr in ipaddress.ip_network(network):
                break
        except ValueError:
            continue
    else:
        return None
    return "[%s]" % addr if addr.version == 6 else str(addr)
