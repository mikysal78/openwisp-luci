import time
import uuid

import pytest
from django.core import signing

from openwisp_luci import access

PK = uuid.UUID("05cb6ac3-10a3-4cf3-8968-e1868fe95e34")
TEMPLATE = "{id}.luci.example.com"


def test_device_host():
    assert access.device_host(TEMPLATE, PK) == "05cb6ac310a34cf38968e1868fe95e34.luci.example.com"
    assert access.device_host(None, PK) is None
    assert access.device_host("luci.example.com", PK) is None
    assert access.device_host("{id}.{id}.example.com", PK) is None


@pytest.mark.parametrize(
    "host,expected",
    [
        ("05cb6ac310a34cf38968e1868fe95e34.luci.example.com", PK.hex),
        ("05CB6AC310A34CF38968E1868FE95E34.LUCI.EXAMPLE.COM", PK.hex),
        ("05cb6ac310a34cf38968e1868fe95e34.luci.example.com.", PK.hex),
        ("05cb6ac310a34cf38968e1868fe95e3.luci.example.com", None),
        ("x05cb6ac310a34cf38968e1868fe95e34.luci.example.com", None),
        ("05cb6ac310a34cf38968e1868fe95e34.luci.example.com.evil.org", None),
        ("05cb6ac310a34cf38968e1868fe95e34.luciXexample.com", None),
        ("openwisp.example.com", None),
        ("", None),
    ],
)
def test_host_device_id(host, expected):
    assert access.host_device_id(TEMPLATE, host) == expected


def test_token_round_trip():
    token = access.make_token(7, PK, "f" * 32)
    data = access.read_token(token, 60)
    assert data["u"] == "7" and data["d"] == PK.hex and data["f"] == "f" * 32 and len(data["n"]) > 10
    # due token per lo stesso device hanno nonce diversi
    assert access.read_token(access.make_token(7, PK, "f" * 32), 60)["n"] != data["n"]


def test_token_and_cookie_are_not_interchangeable():
    token = access.make_token(7, PK, "f" * 32)
    cookie = access.make_cookie(7, PK.hex, "f" * 32)
    assert access.read_cookie(token, 3600) is None
    assert access.read_token(cookie, 60) is None


@pytest.mark.parametrize(
    "value",
    [
        "",
        "x",
        "a" * 2000,
        None,
        signing.dumps({"u": "7"}, salt=access.TOKEN_SALT),
        signing.dumps(["u", "d"], salt=access.TOKEN_SALT),
        signing.dumps({"u": 7, "d": "x", "f": "y", "n": "z"}, salt=access.TOKEN_SALT),
    ],
)
def test_token_rejected(value):
    assert access.read_token(value, 60) is None


def test_token_tampered():
    token = access.make_token(7, PK, "f" * 32)
    head, sig = token.rsplit(":", 1)
    assert access.read_token(head + ":" + sig[::-1], 60) is None


def test_token_expired(monkeypatch):
    token = access.make_token(7, PK, "f" * 32)
    now = time.time()
    monkeypatch.setattr(time, "time", lambda: now + 120)
    assert access.read_token(token, 60) is None


def test_cookie_round_trip():
    data = access.read_cookie(access.make_cookie(7, PK.hex, "f" * 32), 3600)
    assert data == {"u": "7", "d": PK.hex, "f": "f" * 32}


class User:
    def __init__(self, auth_hash):
        self.auth_hash = auth_hash

    def get_session_auth_hash(self):
        return self.auth_hash


def test_fingerprint_changes_with_password():
    a = access.user_fingerprint(User("hash-1"))
    assert a == access.user_fingerprint(User("hash-1"))
    assert a != access.user_fingerprint(User("hash-2"))
    assert len(a) == 32 and "hash" not in a


ALLOWED = ["10.0.0.0/8", "fc00::/7"]


@pytest.mark.parametrize(
    "ip,expected",
    [
        ("10.27.22.230", "10.27.22.230"),
        (" 10.27.22.230 ", "10.27.22.230"),
        ("fd06:a670:beba::1", "[fd06:a670:beba::1]"),
        ("::ffff:10.1.2.3", "10.1.2.3"),
        ("192.168.1.1", None),
        ("127.0.0.1", None),
        ("::1", None),
        ("::ffff:127.0.0.1", None),
        ("169.254.1.1", None),
        ("fe80::1", None),
        ("0.0.0.0", None),
        ("224.0.0.1", None),
        ("2a07:7e81:3f1c::57e", None),
        ("10.27.22.230:8080", None),
        ("10.27.22.230/24", None),
        ("example.com", None),
        ("", None),
        (None, None),
    ],
)
def test_upstream(ip, expected):
    assert access.upstream(ip, ALLOWED) == expected


def test_upstream_bad_network_ignored():
    assert access.upstream("10.1.1.1", ["not a network", "10.0.0.0/8"]) == "10.1.1.1"
    assert access.upstream("10.1.1.1", []) is None
