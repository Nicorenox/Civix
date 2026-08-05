import json

from django.http import JsonResponse

from .domain.exceptions import (
    ProyectoInvalidoError,
    LimiteSuscripcionExcedido,
)
from .models import Empresa, Suscripcion
from .services import ProyectoService
from .infra.factories import NotificadorFactory


def crear_proyecto_response(empresa_id, body):

    try:
        datos = json.loads(body or "{}")

        proyecto = ProyectoService(
            NotificadorFactory
        ).crear_proyecto(
            empresa_id,
            datos,
        )

        return JsonResponse(
            {
                "id": str(proyecto.id),
                "nombre": proyecto.nombre,
                "estado": proyecto.estado,
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON invalido."},
            status=400,
        )

    except ProyectoInvalidoError as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )

    except LimiteSuscripcionExcedido as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )

    except Suscripcion.DoesNotExist:
        return JsonResponse(
            {"error": "La empresa no tiene una suscripcion activa."},
            status=400,
        )

    except Empresa.DoesNotExist:
        return JsonResponse(
            {"error": "Empresa no encontrada."},
            status=404,
        )

=======

import json

from django.http import JsonResponse

from .domain.exceptions import (
    ProyectoInvalidoError,
    LimiteSuscripcionExcedido,
)
from .models import Empresa, Suscripcion
from .services import ProyectoService
from .infra.factories import NotificadorFactory


def crear_proyecto_response(empresa_id, body):

    try:
        datos = json.loads(body or "{}")

        proyecto = ProyectoService(
            NotificadorFactory
        ).crear_proyecto(
            empresa_id,
            datos,
        )

        return JsonResponse(
            {
                "id": str(proyecto.id),
                "nombre": proyecto.nombre,
                "estado": proyecto.estado,
            },
            status=201,
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "JSON invalido."},
            status=400,
        )

    except ProyectoInvalidoError as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )

    except LimiteSuscripcionExcedido as e:
        return JsonResponse(
            {"error": str(e)},
            status=400,
        )

    except Suscripcion.DoesNotExist:
        return JsonResponse(
            {"error": "La empresa no tiene una suscripcion activa."},
            status=400,
        )

    except Empresa.DoesNotExist:
        return JsonResponse(
            {"error": "Empresa no encontrada."},
            status=404,
        )


