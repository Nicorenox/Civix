from django.shortcuts import get_object_or_404, render
from django.views import View
from .models import Empresa
from .handlers import crear_proyecto_response

class CrearProyectoPageView(View):

    def get(self, request, empresa_id):
        empresa = get_object_or_404(Empresa, id=empresa_id)

        return render(
            request,
            "proyectos/crear_proyecto.html",
            {
                "empresa": empresa,
                "api_url": f"/api/empresas/{empresa.id}/proyectos/",
            },
        )
        
class CrearProyectoView(View):

    def post(self, request, empresa_id):
        return crear_proyecto_response(
            empresa_id,
            request.body,
        )