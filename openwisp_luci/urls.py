from django.urls import path

from . import views

app_name = "openwisp_luci"

# Da includere nelle URL del progetto con il prefisso che usa nginx:
#   path("__openwisp_luci__/", include("openwisp_luci.urls")),
urlpatterns = [
    path("login/", views.login, name="login"),
    path("auth/", views.auth, name="auth"),
    path("denied/", views.denied, name="denied"),
]
