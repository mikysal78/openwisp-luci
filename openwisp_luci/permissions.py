from swapper import load_model

from . import access
from . import settings as app_settings

Device = load_model("config", "Device")


def can_open(user, device):
    """Chi puo' aprire LuCI: staff attivo con il permesso di modificare il
    device nella sua organizzazione (LuCI da' il controllo del router)."""
    if not user.is_active or not user.is_staff:
        return False
    if user.is_superuser:
        return True
    if app_settings.SUPERUSER_ONLY:
        return False
    perm = "%s.change_%s" % (Device._meta.app_label, Device._meta.model_name)
    return user.has_perm(perm) and user.is_manager(device.organization_id)


def device_upstream(device):
    if not device.management_ip:
        return None
    return access.upstream(device.management_ip, app_settings.ALLOWED_NETWORKS)
