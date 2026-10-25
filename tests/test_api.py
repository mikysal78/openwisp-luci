"""API del link LuCI con token, utenti e device finti (niente database)."""

import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import RequestFactory

from openwisp_luci import access, api

PK = uuid.UUID("05cb6ac3-10a3-4cf3-8968-e1868fe95e34")
GOOD = "a" * 40


class FakeUser:
    def __init__(self, active=True, allowed=True):
        self.pk, self.username, self.is_active, self.allowed = 7, "admin", active, allowed

    def get_session_auth_hash(self):
        return "h1"


class FakeDevice:
    class DoesNotExist(Exception):
        pass

    def __init__(self, ip="10.27.22.230"):
        self.pk, self.name, self.management_ip = PK, "X5000R", ip


class Manager:
    def __init__(self, items, exc):
        self.items, self.exc = items, exc
        self.keys = []

    def select_related(self, *args):
        return self

    def get(self, **kwargs):
        (value,) = kwargs.values()
        self.keys.append(value)
        if str(value) not in self.items:
            raise self.exc
        return self.items[str(value)]


@pytest.fixture
def world(monkeypatch):
    user = FakeUser()
    device = FakeDevice()

    class Token:
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        objects = None

    Token.objects = Manager({GOOD: type("T", (), {"user": user})()}, Token.DoesNotExist)

    class DeviceModel:
        DoesNotExist = FakeDevice.DoesNotExist
        objects = Manager({str(PK): device}, FakeDevice.DoesNotExist)

    monkeypatch.setattr(api, "_token_model", lambda: Token)
    monkeypatch.setattr(api, "Device", DeviceModel)
    monkeypatch.setattr(api, "can_open", lambda u, d: u.allowed)
    monkeypatch.setattr(api, "device_upstream", lambda d: access.upstream(d.management_ip, ["10.0.0.0/8"]))
    return user, device, Token


rf = RequestFactory()


def call(auth="Bearer " + GOOD, method="post", pk=PK):
    kwargs = {"HTTP_AUTHORIZATION": auth} if auth is not None else {}
    request = getattr(rf, method)(
        "/api/v1/luci/device/%s/link/" % pk, HTTP_HOST="openwisp.example.com", **kwargs
    )
    return api.link(request, pk=pk)


def test_link(world):
    response = call()
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    url = urlparse(__import__("json").loads(response.content)["url"])
    assert url.scheme == "https" and url.netloc == PK.hex + ".luci.example.com"
    assert url.path == "/__openwisp_luci__/login/"
    data = access.read_token(parse_qs(url.query)["token"][0], 60)
    assert data["u"] == "7" and data["d"] == PK.hex


@pytest.mark.parametrize(
    "auth",
    [
        None,
        "",
        "Bearer",
        "Bearer ",
        "Token " + GOOD,
        "Basic " + GOOD,
        "Bearer " + "b" * 40,
        "Bearer " + "a" * 200,
    ],
)
def test_link_bad_token(world, auth):
    assert call(auth).status_code == 401


def test_link_overlong_token_not_looked_up(world):
    _, _, Token = world
    call("Bearer " + "a" * 200)
    assert Token.objects.keys == []


def test_link_inactive_user(world):
    user, _, _ = world
    user.is_active = False
    assert call().status_code == 401


def test_link_not_allowed_looks_missing(world):
    user, _, _ = world
    user.allowed = False
    assert call().status_code == 404
    assert call(pk=uuid.uuid4()).status_code == 404


def test_link_bad_ip(world):
    _, device, _ = world
    device.management_ip = "127.0.0.1"
    assert call().status_code == 409
    device.management_ip = None
    assert call().status_code == 409


def test_link_get_refused(world):
    assert call(method="get").status_code == 405


def test_link_disabled(world, monkeypatch):
    monkeypatch.setattr(api.app_settings, "HOST", None)
    assert call().status_code == 404
