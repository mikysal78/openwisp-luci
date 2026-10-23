"""Viste del proxy con utenti e device finti (niente database)."""

import uuid

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from openwisp_luci import access, views

PK = uuid.UUID("05cb6ac3-10a3-4cf3-8968-e1868fe95e34")
OTHER = uuid.UUID("202a7d85-0d3c-4bea-a9f1-f4c49d2579e2")
HOST = PK.hex + ".luci.example.com"


class FakeUser:
    def __init__(self, pk=7, auth_hash="h1", allowed=True, superuser=False):
        self.pk, self.username, self.auth_hash, self.allowed = pk, "admin", auth_hash, allowed
        self.is_superuser = superuser

    def get_session_auth_hash(self):
        return self.auth_hash


class FakeDevice:
    class DoesNotExist(Exception):
        pass

    def __init__(self, pk, ip="10.27.22.230"):
        self.pk, self.name, self.management_ip = pk, "X5000R", ip


class Manager:
    def __init__(self, items, exc):
        self.items, self.exc = items, exc

    def select_related(self, *args):
        return self

    def get(self, pk):
        key = str(pk)
        if key not in self.items:
            raise self.exc
        return self.items[key]


@pytest.fixture
def world(monkeypatch):
    users = {"7": FakeUser()}
    devices = {str(PK): FakeDevice(PK), str(OTHER): FakeDevice(OTHER)}

    class UserModel:
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        objects = None

    UserModel.objects = Manager(users, UserModel.DoesNotExist)

    class DeviceModel:
        DoesNotExist = FakeDevice.DoesNotExist
        objects = Manager(devices, FakeDevice.DoesNotExist)

    monkeypatch.setattr(views, "get_user_model", lambda: UserModel)
    monkeypatch.setattr(views, "Device", DeviceModel)
    monkeypatch.setattr(views, "can_open", lambda user, device: user.allowed)
    monkeypatch.setattr(
        views, "device_upstream", lambda device: access.upstream(device.management_ip, ["10.0.0.0/8"])
    )
    cache.clear()
    return users, devices


rf = RequestFactory()


def token(device=PK, user=None):
    user = user or FakeUser()
    return access.make_token(user.pk, device, access.user_fingerprint(user))


def login(tok, host=HOST):
    return views.login(rf.get("/__openwisp_luci__/login/", {"token": tok}, HTTP_HOST=host, secure=True))


def auth(cookie, host=HOST, method="get"):
    request = getattr(rf, method)("/__openwisp_luci__/auth/", HTTP_HOST=host, secure=True)
    if cookie is not None:
        request.COOKIES[access.COOKIE_NAME] = cookie
    return views.auth(request)


def test_login_sets_cookie(world):
    response = login(token())
    assert response.status_code == 302 and response["Location"] == "/cgi-bin/luci/"
    morsel = response.cookies[access.COOKIE_NAME]
    assert morsel["secure"] and morsel["httponly"] and morsel["samesite"] == "Strict"
    assert morsel["path"] == "/" and not morsel["domain"]
    assert response["Referrer-Policy"] == "no-referrer" and "no-store" in response["Cache-Control"]
    assert auth(morsel.value).status_code == 204


def test_login_single_use(world):
    tok = token()
    assert login(tok).status_code == 302
    assert login(tok).status_code == 403


def test_login_wrong_host(world):
    assert login(token(), host=OTHER.hex + ".luci.example.com").status_code == 403
    assert login(token(), host="openwisp.example.com").status_code == 403


def test_login_wrong_host_does_not_burn_token(world):
    tok = token()
    assert login(tok, host="openwisp.example.com").status_code == 403
    assert login(tok).status_code == 302


@pytest.mark.parametrize("tok", ["", "junk", access.make_cookie(7, PK.hex, "x")])
def test_login_bad_token(world, tok):
    assert login(tok).status_code == 403


def test_login_post_refused(world):
    request = rf.post("/__openwisp_luci__/login/?token=" + token(), HTTP_HOST=HOST, secure=True)
    assert views.login(request).status_code == 405


def test_auth_upstream_header(world):
    cookie = access.make_cookie(7, PK.hex, access.user_fingerprint(FakeUser()))
    response = auth(cookie)
    assert response.status_code == 204
    assert response[access.UPSTREAM_HEADER] == "10.27.22.230"
    # anche con il metodo della richiesta originale
    assert auth(cookie, method="post").status_code == 204


def test_auth_refused(world):
    users, devices = world
    good = access.make_cookie(7, PK.hex, access.user_fingerprint(FakeUser()))
    assert auth(None).status_code == 401
    assert auth("junk").status_code == 401
    # cookie di un device usato sull'host di un altro
    assert auth(good, host=OTHER.hex + ".luci.example.com").status_code == 401
    assert auth(good, host="openwisp.example.com").status_code == 401
    # password cambiata
    users["7"].auth_hash = "h2"
    assert auth(good).status_code == 401
    users["7"].auth_hash = "h1"
    # permesso tolto
    users["7"].allowed = False
    assert auth(good).status_code == 401
    users["7"].allowed = True
    # IP di gestione fuori dalle reti ammesse o mancante
    devices[str(PK)].management_ip = "127.0.0.1"
    assert auth(good).status_code == 401
    devices[str(PK)].management_ip = None
    assert auth(good).status_code == 401
    devices[str(PK)].management_ip = "10.27.22.230"
    # device o utente cancellati
    del devices[str(PK)]
    assert auth(good).status_code == 401
    devices[str(PK)] = FakeDevice(PK)
    del users["7"]
    assert auth(good).status_code == 401


def test_auth_token_is_not_a_cookie(world):
    assert auth(token()).status_code == 401


def test_denied_page(world):
    response = views.denied(rf.get("/__openwisp_luci__/denied/", HTTP_HOST=HOST, secure=True))
    assert response.status_code == 403
    assert b"LuCI" in response.content


SID = "0123456789abcdef0123456789abcdef"


def test_login_auto_login_superuser(world, monkeypatch):
    users, _ = world
    users["7"].is_superuser = True
    calls = []
    monkeypatch.setattr(views.autologin, "router_session", lambda device: calls.append(device) or SID)
    response = login(token())
    assert response.status_code == 302 and len(calls) == 1
    morsel = response.cookies["sysauth_https"]
    assert morsel.value == SID and morsel["path"] == "/cgi-bin/luci/"
    assert morsel["secure"] and morsel["httponly"] and morsel["samesite"] == "Strict"
    assert not morsel["domain"]


def test_login_no_auto_login_for_others(world, monkeypatch):
    calls = []
    monkeypatch.setattr(views.autologin, "router_session", lambda device: calls.append(device) or SID)
    response = login(token())
    assert response.status_code == 302 and not calls
    assert "sysauth_https" not in response.cookies


def test_login_auto_login_failed(world, monkeypatch):
    users, _ = world
    users["7"].is_superuser = True
    monkeypatch.setattr(views.autologin, "router_session", lambda device: None)
    response = login(token())
    assert response.status_code == 302 and "sysauth_https" not in response.cookies
    assert access.COOKIE_NAME in response.cookies
