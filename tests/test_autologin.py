"""Sessione LuCI creata via SSH: comando, parsing e connessione finta."""

import shlex
import threading

import pytest

from openwisp_luci import autologin
from openwisp_luci import settings as app_settings

SID = "0123456789abcdef0123456789abcdef"


def test_command_quotes_script():
    cmd = autologin.command("admin")
    argv = shlex.split(cmd)
    assert argv[:2] == ["ucode", "-e"] and len(argv) == 3
    assert 'let user = "admin";' in argv[2] and "__USER__" not in argv[2]
    assert 'bus.call("session", "create"' in argv[2]


@pytest.mark.parametrize("user", ["", "root; reboot", 'a"b', "Admin", "a" * 40, None])
def test_command_refuses_bad_user(user):
    with pytest.raises(ValueError):
        autologin.command(user)


@pytest.mark.parametrize(
    "output, sid",
    [(SID + "\n", SID), (SID, SID), ("", None), ("junk\n", None), (SID + "x", None), (SID.upper(), None)],
)
def test_parse_sid(output, sid):
    assert autologin.parse_sid(output) == sid


class FakeChannel:
    def __init__(self, status, done=True):
        self.exit_status = status
        self.status_event = threading.Event()
        if done:
            self.status_event.set()


class FakeStdout:
    def __init__(self, output, status, done=True):
        self.output, self.channel = output, FakeChannel(status, done)

    def read(self):
        return self.output.encode()


class FakeShell:
    def __init__(self, output, status, done=True, exc=None):
        self.args, self.result, self.exc = None, (None, FakeStdout(output, status, done), None), exc

    def exec_command(self, cmd, timeout):
        self.args = cmd, timeout
        if self.exc:
            raise self.exc
        return self.result


class FakeConnection:
    def __init__(self, shell):
        self.connector_instance = type("C", (), {"shell": shell})()
        self.disconnected = False

    def disconnect(self):
        self.disconnected = True


class FakeDevice:
    name = "X5000R"


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(app_settings, "AUTO_LOGIN", True)
    monkeypatch.setattr(app_settings, "AUTO_LOGIN_TIMEOUT", 0.05)


def use(monkeypatch, shell):
    conn = FakeConnection(shell)
    monkeypatch.setattr(autologin, "_connection", lambda device: conn)
    return conn


def test_router_session_ok(enabled, monkeypatch):
    shell = FakeShell(SID + "\n", 0)
    conn = use(monkeypatch, shell)
    assert autologin.router_session(FakeDevice()) == SID
    assert shell.args[0].startswith("ucode -e ") and conn.disconnected


@pytest.mark.parametrize(
    "shell",
    [
        FakeShell(SID, 2),
        FakeShell("utente rpcd non trovato\n", 0),
        FakeShell(SID, 0, done=False),
        FakeShell(SID, 0, exc=OSError("broken pipe")),
    ],
)
def test_router_session_failures(enabled, monkeypatch, shell, caplog):
    conn = use(monkeypatch, shell)
    assert autologin.router_session(FakeDevice()) is None
    assert conn.disconnected
    assert SID not in caplog.text


def test_router_session_no_connection(enabled, monkeypatch):
    def fail(device):
        raise RuntimeError("no working connection")

    monkeypatch.setattr(autologin, "_connection", fail)
    assert autologin.router_session(FakeDevice()) is None


def test_router_session_disabled(monkeypatch):
    monkeypatch.setattr(app_settings, "AUTO_LOGIN", False)
    monkeypatch.setattr(autologin, "_connection", lambda device: pytest.fail("no SSH when disabled"))
    assert autologin.router_session(FakeDevice()) is None


def test_router_session_bad_user(enabled, monkeypatch):
    monkeypatch.setattr(app_settings, "AUTO_LOGIN_USER", "root; reboot")
    monkeypatch.setattr(autologin, "_connection", lambda device: pytest.fail("no SSH with a bad user"))
    assert autologin.router_session(FakeDevice()) is None
