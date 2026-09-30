from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def inicio(request):
    return JsonResponse({
        "proyecto": "Civix",
        "mensaje": "API disponible.",
        "endpoints": "/api/",
        "interfaz": "/api/empresas/<empresa_id>/proyectos/crear/",
    })


urlpatterns = [
    path("", inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("api/", include("proyectos.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
