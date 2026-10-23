from django.urls import include, path

urlpatterns = [path("__openwisp_luci__/", include("openwisp_luci.urls"))]
