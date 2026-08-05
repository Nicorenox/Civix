from django.urls import path
from .views import CrearProyectoPageView, CrearProyectoView

urlpatterns = [
    path(
        "empresas/<uuid:empresa_id>/proyectos/crear/",
        CrearProyectoPageView.as_view(),
        name="crear_proyecto_page",
    ),
    path(
        "empresas/<uuid:empresa_id>/proyectos/",
        CrearProyectoView.as_view(),
        name="crear_proyecto",
    ),
]
