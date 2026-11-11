from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from django.conf.urls.i18n import set_language


def inicio(request):
    # La raíz presenta la aplicación; las rutas /api/ siguen disponibles para
    # clientes y para la documentación de la arquitectura del entregable.
    return render(request, "proyectos/inicio.html")


urlpatterns = [
    path("", inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("api/", include("proyectos.urls")),
    path("i18n/setlang/", set_language, name="set_language"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
