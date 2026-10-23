from django.conf import settings

# Nome host del proxy per ogni device: {id} diventa l'UUID del device senza
# trattini, per esempio "{id}.luci.example.com" (DNS e certificato wildcard
# *.luci.example.com). Un host per device = un'origine per router: cookie e
# JavaScript di un router non vedono quelli degli altri. None = funzione spenta.
HOST = getattr(settings, "OPENWISP_LUCI_HOST", None)
# Reti in cui puo' stare l'IP di gestione del device: l'IP lo dichiara il
# router, quindi senza questo limite un router potrebbe far puntare il proxy a
# un servizio del server o di un'altra rete. Loopback, link-local, multicast e
# indirizzi riservati sono rifiutati comunque.
ALLOWED_NETWORKS = getattr(
    settings,
    "OPENWISP_LUCI_ALLOWED_NETWORKS",
    ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"],
)
# Secondi di validita' del link monouso che apre il proxy
TOKEN_AGE = getattr(settings, "OPENWISP_LUCI_TOKEN_AGE", 60)
# Secondi di validita' del cookie del proxy (poi si riapre da OpenWISP)
SESSION_AGE = getattr(settings, "OPENWISP_LUCI_SESSION_AGE", 4 * 3600)
# Solo i superuser possono aprire LuCI
SUPERUSER_ONLY = getattr(settings, "OPENWISP_LUCI_SUPERUSER_ONLY", False)
# Indirizzo di OpenWISP (es. "https://openwisp.example.com") per il link nella
# pagina di accesso negato; None = nessun link
OPENWISP_URL = getattr(settings, "OPENWISP_LUCI_OPENWISP_URL", None)
