from django.urls import path

from .views import (
    CrearProyectoPageView,
    LoginPageView,
    PanelPageView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    ProyectoListCreateAPIView,
    ProyectoDetailAPIView,
    InspeccionListCreateAPIView,
    InspeccionCorregirAPIView,
    InspeccionConfirmarAPIView,
    BitacoraProyectoAPIView,
)

urlpatterns = [
    # --- Interfaz HTML ---
    path(
        "empresas/<uuid:empresa_id>/proyectos/crear/",
        CrearProyectoPageView.as_view(),
        name="crear_proyecto_page",
    ),
    path("login/", LoginPageView.as_view(), name="login_page"),
    path("panel/", PanelPageView.as_view(), name="panel_page"),

    # --- Autenticacion ---
    path("auth/login/", LoginAPIView.as_view(), name="auth_login"),
    path("auth/logout/", LogoutAPIView.as_view(), name="auth_logout"),
    path("auth/me/", MeAPIView.as_view(), name="auth_me"),

    # --- Proyecto ---
    path(
        "empresas/<uuid:empresa_id>/proyectos/",
        ProyectoListCreateAPIView.as_view(),
        name="crear_proyecto",
    ),
    path(
        "proyectos/<uuid:proyecto_id>/",
        ProyectoDetailAPIView.as_view(),
        name="detalle_proyecto",
    ),
    path(
        "proyectos/<uuid:proyecto_id>/bitacora/",
        BitacoraProyectoAPIView.as_view(),
        name="bitacora_proyecto",
    ),

    # --- Inspeccion ---
    path(
        "proyectos/<uuid:proyecto_id>/inspecciones/",
        InspeccionListCreateAPIView.as_view(),
        name="crear_inspeccion",
    ),
    path(
        "inspecciones/<uuid:inspeccion_id>/corregir/",
        InspeccionCorregirAPIView.as_view(),
        name="corregir_inspeccion",
    ),
    path(
        "inspecciones/<uuid:inspeccion_id>/confirmar/",
        InspeccionConfirmarAPIView.as_view(),
        name="confirmar_inspeccion",
    ),
]
