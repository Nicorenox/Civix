from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def inicio(request):
    return JsonResponse({
        "proyecto": "Civix",
        "mensaje": "API disponible.",
        "endpoint": "POST /api/empresas/<empresa_id>/proyectos/",
        "interfaz": "/api/empresas/<empresa_id>/proyectos/crear/",
    })


urlpatterns = [
    path("", inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("api/", include("proyectos.urls")),
]
