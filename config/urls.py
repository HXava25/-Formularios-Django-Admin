from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from solicitudes import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard, name="dashboard"),
    path("registro/", views.registro, name="registro"),
    path(
        "ingresar/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("solicitudes/nueva/", views.solicitud_crear, name="solicitud_crear"),
    path("solicitudes/<int:pk>/", views.solicitud_detalle, name="solicitud_detalle"),
    path(
        "solicitudes/<int:pk>/estado/",
        views.SolicitudEstadoView.as_view(),
        name="solicitud_estado",
    ),
]
