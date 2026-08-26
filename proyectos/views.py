from django.shortcuts import get_object_or_404, render
from django.views import View

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from .services import ProyectoService, InspeccionService
from .services.auth_service import AuthService
from .infra.factories import NotificadorFactory
from .domain.exceptions import (
    ProyectoInvalidoError,
    LimiteSuscripcionExcedido,
    InspeccionInvalidaError,
    TransicionInvalidaError,
    CredencialesInvalidasError,
)
from .models import Empresa, Suscripcion, Proyecto, Inspeccion, Usuario
from .serializers import (
    ProyectoSerializer,
    ProyectoCreateSerializer,
    InspeccionSerializer,
    InspeccionCreateSerializer,
    InspeccionCorregirSerializer,
    InspeccionConfirmarSerializer,
    RegistroBitacoraSerializer,
    LoginSerializer,
    UsuarioSerializer,
)


# ---------------------------------------------------------------------
# Paginas HTML (para la sustentacion presencial)
# ---------------------------------------------------------------------
class CrearProyectoPageView(View):
    """Interfaz HTML para crear un proyecto (sin cambios respecto al taller)."""

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


class LoginPageView(View):
    """Pantalla de login (HTML). El formulario llama a /api/auth/login/."""

    def get(self, request):
        return render(request, "proyectos/login.html")


class PanelPageView(View):
    """
    Panel unico adaptativo: tras el login, el propio JS decide (segun el
    rol devuelto por /api/auth/login/) que secciones mostrar -
    operativas (crear proyecto/inspeccion, confirmar) o gerenciales
    (solo consulta). Asi se demuestran los flujos de los PASOS 1-12
    desde un unico lugar, sin construir dos aplicaciones separadas.
    """

    def get(self, request):
        return render(request, "proyectos/panel.html")


# ---------------------------------------------------------------------
# Autenticacion (PASO 12 - preparada, no forzada por defecto)
# ---------------------------------------------------------------------
class LoginAPIView(APIView):
    """
    Login SIN 2FA/mTLS todavia (ver AuthService para los puntos de
    extension futura). Emite un SesionToken que el cliente debe enviar
    como 'Authorization: Token <token>' en peticiones posteriores.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = LoginSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        try:
            usuario, sesion = AuthService().iniciar_sesion(
                correo=datos["correo"],
                contrasena=datos["contrasena"],
                dispositivo=datos.get("dispositivo", ""),
            )
        except CredencialesInvalidasError as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(
            {"token": sesion.token, "usuario": UsuarioSerializer(usuario).data},
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    """Invalida el SesionToken enviado en el body."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "")
        if token:
            AuthService().cerrar_sesion(token)
        return Response(status=status.HTTP_200_OK)


class MeAPIView(APIView):
    """
    Endpoint DE EJEMPLO con la seguridad ya ACTIVADA (permission_classes
    = [IsAuthenticated]): asi se ve exactamente como "encender" la
    autenticacion en cualquier otra vista del sistema mas adelante.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


# ---------------------------------------------------------------------
# Proyecto
# ---------------------------------------------------------------------
class ProyectoListCreateAPIView(APIView):
    """
    Capa de Presentacion (DRF). Lista y crea Proyectos de una Empresa.
    El Serializer solo valida formato; ProyectoService aplica las reglas
    de negocio (limites de suscripcion, fechas, Builder).
    """

    def get(self, request, empresa_id):
        if not Empresa.objects.filter(id=empresa_id).exists():
            return Response(
                {"error": "Empresa no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        proyectos = Proyecto.objects.filter(empresa_id=empresa_id)
        return Response(ProyectoSerializer(proyectos, many=True).data)

    def post(self, request, empresa_id):
        if not Empresa.objects.filter(id=empresa_id).exists():
            return Response(
                {"error": "Empresa no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        entrada = ProyectoCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        service = ProyectoService(notificador=NotificadorFactory.crear())
        try:
            proyecto = service.crear_proyecto(
                empresa_id=empresa_id,
                nombre=datos["nombre"],
                descripcion=datos.get("descripcion", ""),
                fecha_inicio=datos.get("fechaInicio"),
                fecha_fin=datos.get("fechaFin"),
            )
        except (ProyectoInvalidoError, LimiteSuscripcionExcedido) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Suscripcion.DoesNotExist:
            return Response(
                {"error": "La empresa no tiene una suscripcion activa."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ProyectoSerializer(proyecto).data, status=status.HTTP_201_CREATED
        )


class ProyectoDetailAPIView(APIView):
    """Detalle de un proyecto (equivalente al 'resumen ejecutivo' de los mockups)."""

    def get(self, request, proyecto_id):
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)
        return Response(ProyectoSerializer(proyecto).data)


# ---------------------------------------------------------------------
# Inspeccion
# ---------------------------------------------------------------------
class InspeccionListCreateAPIView(APIView):
    """
    Capa de Presentacion (DRF). Lista (con filtro opcional ?estado=) y
    crea Inspecciones de un Proyecto. Acepta multipart/form-data para
    soportar fotografias adjuntas (request.FILES.getlist).
    """

    def get(self, request, proyecto_id):
        if not Proyecto.objects.filter(id=proyecto_id).exists():
            return Response(
                {"error": "Proyecto no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        inspecciones = Inspeccion.objects.filter(
            proyecto_id=proyecto_id
        ).order_by("-creado_en")

        estado = request.query_params.get("estado")
        if estado:
            inspecciones = inspecciones.filter(estado=estado)

        return Response(InspeccionSerializer(inspecciones, many=True).data)

    def post(self, request, proyecto_id):
        if not Proyecto.objects.filter(id=proyecto_id).exists():
            return Response(
                {"error": "Proyecto no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        entrada = InspeccionCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        if not Usuario.objects.filter(id=datos["usuario_id"]).exists():
            return Response(
                {"error": "Usuario inspector no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        fotografias = request.FILES.getlist("fotografias")

        service = InspeccionService(notificador=NotificadorFactory.crear())
        try:
            inspeccion = service.crear_inspeccion(
                proyecto_id=proyecto_id,
                inspector_id=datos["usuario_id"],
                tipo_inspeccion=datos.get("tipo_inspeccion"),
                observaciones=datos.get("observaciones", ""),
                fecha_visita=datos["fecha_visita"],
                porcentaje_avance_reportado=datos["porcentaje_avance_reportado"],
                fotografias=fotografias,
            )
        except InspeccionInvalidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            InspeccionSerializer(inspeccion).data, status=status.HTTP_201_CREATED
        )


class InspeccionCorregirAPIView(APIView):
    """Caso de uso: Corregir Inspeccion (solo mientras esta PENDIENTE)."""

    def patch(self, request, inspeccion_id):
        if not Inspeccion.objects.filter(id=inspeccion_id).exists():
            return Response(
                {"error": "Inspeccion no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        entrada = InspeccionCorregirSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        service = InspeccionService(notificador=NotificadorFactory.crear())
        try:
            inspeccion = service.corregir_inspeccion(
                inspeccion_id=inspeccion_id,
                observaciones=datos.get("observaciones"),
                porcentaje_avance_reportado=datos.get("porcentaje_avance_reportado"),
                usuario_id=datos.get("usuario_id"),
            )
        except TransicionInvalidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except InspeccionInvalidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InspeccionSerializer(inspeccion).data, status=status.HTTP_200_OK)


class InspeccionConfirmarAPIView(APIView):
    """
    Caso de uso mas complejo del sistema: Confirmar Inspeccion.
    Al confirmar, el Service actualiza oficialmente Proyecto.porcentaje_avance
    y escribe la bitacora. Si la inspeccion ya no esta PENDIENTE, responde 409
    (Conflict), no 400: los datos de la peticion son correctos, el problema
    es el ESTADO del recurso.
    """

    def post(self, request, inspeccion_id):
        if not Inspeccion.objects.filter(id=inspeccion_id).exists():
            return Response(
                {"error": "Inspeccion no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        entrada = InspeccionConfirmarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        service = InspeccionService(notificador=NotificadorFactory.crear())
        try:
            inspeccion = service.confirmar_inspeccion(
                inspeccion_id=inspeccion_id,
                usuario_id=datos.get("usuario_id"),
            )
        except TransicionInvalidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response(InspeccionSerializer(inspeccion).data, status=status.HTTP_200_OK)


class BitacoraProyectoAPIView(APIView):
    """Historial de bitacora de un proyecto (pantalla 'Bitacora de inspecciones')."""

    def get(self, request, proyecto_id):
        proyecto = get_object_or_404(Proyecto, id=proyecto_id)
        registros = proyecto.bitacora.all()
        return Response(RegistroBitacoraSerializer(registros, many=True).data)
