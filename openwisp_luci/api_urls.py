from django.urls import path

from . import api

app_name = "openwisp_luci_api"

# Da includere nelle URL del progetto accanto alle altre API di OpenWISP:
#   path("api/v1/", include("openwisp_luci.api_urls")),
urlpatterns = [
    path("luci/device/<uuid:pk>/link/", api.link, name="link"),
]
