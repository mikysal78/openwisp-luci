from django.urls import include, path

urlpatterns = [
    path("__openwisp_luci__/", include("openwisp_luci.urls")),
    path("api/v1/", include("openwisp_luci.api_urls")),
]
