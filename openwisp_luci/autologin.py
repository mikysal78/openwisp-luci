"""Sessione LuCI creata dal server, per l'accesso automatico dei superuser.

OpenWISP ha gia' una connessione SSH a ogni router (Credentials): la si usa
per eseguire router_session.uc, che crea una sessione rpcd per l'utente
AUTO_LOGIN_USER con le ACL che rpcd gli darebbe al login, e ne stampa l'ID.
Nessuna password sul server. Il comando passa direttamente dal canale SSH di
paramiko e non da exec_command di openwisp-controller, che scrive l'output nel
log: l'ID della sessione e' una credenziale e non deve finire nei log.
"""

import json
import logging
import re
import shlex
from importlib.resources import files

from . import settings as app_settings

logger = logging.getLogger(__name__)

# cookie di LuCI quando il router e' raggiunto in HTTPS (il proxy usa HTTPS)
COOKIE_NAME = "sysauth_https"
COOKIE_PATH = "/cgi-bin/luci/"
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
SID_RE = re.compile(r"^[0-9a-f]{32}$")


def command(user):
    if not USER_RE.match(user or ""):
        raise ValueError("invalid router user")
    script = files("openwisp_luci").joinpath("router_session.uc").read_text()
    return "ucode -e " + shlex.quote(script.replace("__USER__", json.dumps(user)))


def parse_sid(output):
    sid = output.strip()
    return sid if SID_RE.match(sid) else None


def _connection(device):
    from swapper import load_model

    return load_model("connection", "DeviceConnection").get_working_connection(device)


def router_session(device):
    """ID della nuova sessione LuCI sul router, o None se non si e' potuta creare."""
    if not app_settings.AUTO_LOGIN:
        return None
    try:
        cmd = command(app_settings.AUTO_LOGIN_USER)
        conn = _connection(device)
    except Exception as e:
        logger.warning("accesso automatico a %s non disponibile: %s", device.name, type(e).__name__)
        return None
    try:
        timeout = float(app_settings.AUTO_LOGIN_TIMEOUT)
        _, stdout, _ = conn.connector_instance.shell.exec_command(cmd, timeout=timeout)
        if not stdout.channel.status_event.wait(timeout=timeout):
            raise TimeoutError
        output = stdout.read().decode("ascii", "ignore")
        status = stdout.channel.exit_status
    except Exception as e:
        logger.warning("sessione LuCI non creata su %s: %s", device.name, type(e).__name__)
        return None
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass
    sid = parse_sid(output) if status == 0 else None
    if sid is None:
        logger.warning("sessione LuCI non creata su %s: uscita %s", device.name, status)
    return sid
