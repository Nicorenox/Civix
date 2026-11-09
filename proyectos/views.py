import hmac
import json
import os
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
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
    DemoProvisionSerializer,
    UsuarioSerializer,
)
from .infra.adapters import aliado_adapter, terceros_adapter
from .tasks import generar_reporte
from celery.result import AsyncResult


class IntegracionesAPIView(APIView):
    """Facade para el servicio aliado y el tercero: ambos pasan por Adapter."""
    def get(self, request):
        return Response({"aliado": aliado_adapter().obtener_resumen(),
                         "tercero": terceros_adapter().obtener_referencia()})


class SuscripcionesLocalProxyAPIView(APIView):
    """Puente de desarrollo para acceder a Flask sin ejecutar Nginx localmente.

    En Docker Compose, Nginx enruta directamente /api/v2/suscripciones/ a Flask.
    Este puente solo se usa al arrancar Django y Flask en dos procesos locales.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def _forward(self, request, suffix, method):
        base = getattr(settings, "SUBSCRIPTIONS_SERVICE_URL", "http://127.0.0.1:5001")
        headers = {"Accept": "application/json", "Accept-Language": request.headers.get("Accept-Language", "es")}
        body = None
        if method == "POST":
            headers["Content-Type"] = "application/json"
            body = json.dumps(request.data).encode("utf-8")
        outgoing = Request(f"{base.rstrip('/')}/api/v2/suscripciones/{suffix}", data=body,
                           headers=headers, method=method)
        try:
            with urlopen(outgoing, timeout=10) as response:
                return Response(json.loads(response.read().decode("utf-8")), status=response.status)
        except HTTPError as error:
            try:
                data = json.loads(error.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                data = {"error": "El servicio de suscripciones devolvió una respuesta inválida."}
            return Response(data, status=error.code)
        except (URLError, TimeoutError, ValueError, UnicodeDecodeError):
            return Response({"error": "El microservicio de suscripciones no está disponible."}, status=503)

    def get(self, request):
        return self._forward(request, "planes/", "GET")

    def post(self, request):
        return self._forward(request, "checkout/", "POST")


class ReporteAsyncAPIView(APIView):
    """Encola reportes mediante Celery/Redis y permite consultar su estado."""
    def post(self, request):
        empresa_id = request.data.get("empresa_id")
        if not empresa_id or not Empresa.objects.filter(id=empresa_id).exists():
            return Response({"error": "empresa_id válido es obligatorio."}, status=400)
        # En ejecución local normalmente no hay Redis/Celery worker. Ejecutar
        # la misma tarea en modo directo evita que la descarga quede esperando
        # indefinidamente; Compose en AWS define ENV_TYPE=MICROSERVICIO y usa
        # el flujo real de cola asíncrona que exige la arquitectura.
        if os.environ.get("ENV_TYPE", "LOCAL").upper() == "LOCAL":
            return Response({"estado": "success", "resultado": generar_reporte.run(str(empresa_id))})
        try:
            tarea = generar_reporte.delay(str(empresa_id))
            return Response({"task_id": tarea.id, "estado": "encolado"}, status=202)
        except Exception:
            # Si Redis no está disponible en una ejecución local, la demo aún
            # puede entregar el reporte. En EC2 se usa el worker Celery.
            return Response({"estado": "success", "resultado": generar_reporte.run(str(empresa_id))})

    def get(self, request, task_id=None):
        if not task_id:
            return Response({"error": "task_id es obligatorio."}, status=400)
        tarea = AsyncResult(task_id)
        respuesta = {"task_id": task_id, "estado": tarea.state.lower()}
        if tarea.successful():
            respuesta["resultado"] = tarea.result
        elif tarea.failed():
            respuesta["error"] = "No fue posible generar el reporte."
        return Response(respuesta)


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


class ProyectoPageView(View):
    """Ficha HTML independiente: carga datos e historial desde las APIs Civix."""

    def get(self, request, proyecto_id):
        return render(request, "proyectos/proyecto_detalle.html", {"proyecto_id": proyecto_id})


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


class DemoProvisionAPIView(APIView):
    """Endpoint interno: registra empresa, suscripción demo y su administrador.

    Solo el microservicio Flask puede llamarlo usando un secreto compartido.
    Nginx rechaza el prefijo /api/internal/ desde Internet; la app Django no
    confía en campos de la interfaz para asignar el plan o el rol.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        secreto_configurado = getattr(settings, "DEMO_PROVISION_TOKEN", "")
        secreto_recibido = request.headers.get("X-Civix-Service-Token", "")
        if (len(secreto_configurado) < 32 or
                not hmac.compare_digest(secreto_recibido, secreto_configurado)):
            return Response({"error": "Servicio interno no autorizado."}, status=403)

        entrada = DemoProvisionSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        correo = datos["correo_usuario"].strip().lower()
        nit = datos["nit"].strip()
        if Usuario.objects.filter(correo__iexact=correo).exists():
            return Response({"error": "Ese correo ya tiene una cuenta Civix."}, status=409)
        if Empresa.objects.filter(nit=nit).exists():
            return Response({"error": "Ese NIT ya tiene un espacio registrado."}, status=409)

        # Alta de los tres registros en una sola transacción: nunca queda una
        # empresa creada sin suscripción o sin el administrador inicial.
        hoy = timezone.localdate()
        try:
            with transaction.atomic():
                empresa = Empresa.objects.create(
                    nombre=datos["empresa"].strip(), nit=nit,
                    correo=datos["correo_empresa"].strip().lower(),
                    plan=datos["plan"], estado=Empresa.Estado.ACTIVA,
                )
                suscripcion = Suscripcion.objects.create(
                    empresa=empresa, plan=datos["plan"], fecha_inicio=hoy,
                    fecha_fin=hoy + timedelta(days=30),
                    almacenamiento_gb=Suscripcion.LIMITES_ALMACENAMIENTO_GB[datos["plan"]],
                )
                usuario = Usuario(
                    empresa=empresa, nombre=datos["nombre_usuario"].strip(),
                    correo=correo, rol=Usuario.Rol.ADMINISTRADOR,
                )
                usuario.set_password(datos["contrasena"])
                usuario.save()
        except IntegrityError:
            # Resuelve la carrera entre dos checkouts que intentan registrar
            # el mismo correo/NIT después de pasar las comprobaciones previas.
            return Response({"error": "El correo o NIT ya tiene un espacio Civix."}, status=409)

        return Response({
            "empresa": {"id": str(empresa.id), "nombre": empresa.nombre},
            "usuario": {"nombre": usuario.nombre, "correo": usuario.correo,
                        "rol": usuario.get_rol_display()},
            "suscripcion": {
                "plan": suscripcion.plan,
                "nombre": suscripcion.get_plan_display(),
                "estado": "activa_demo",
                "proyectos_max": Suscripcion.LIMITES_PROYECTOS[suscripcion.plan],
                "almacenamiento_gb": suscripcion.almacenamiento_gb,
                "fecha_fin": suscripcion.fecha_fin.isoformat(),
            },
            "login_url": "/api/login/",
        }, status=status.HTTP_201_CREATED)


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
