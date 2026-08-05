
import json
from datetime import date

from django.db import transaction

from .models import Empresa, Suscripcion
from .domain.builders import ProyectoBuilder
from .domain.exceptions import (
    ProyectoInvalidoError,
    LimiteSuscripcionExcedido,
)


class ProyectoService:

    def __init__(self, notificador_factory):
        self.notificador_factory = notificador_factory

    @transaction.atomic
    def crear_proyecto(self, empresa_id, datos):
        empresa = Empresa.objects.select_for_update().get(id=empresa_id)
        suscripcion = Suscripcion.objects.get(empresa=empresa)

        fecha_inicio = self._parse_date(datos.get("fechaInicio"))
        fecha_fin = self._parse_date(datos.get("fechaFin"))

        self._verificar_limite(empresa, suscripcion)

        proyecto = (
            ProyectoBuilder()
            .para_empresa(empresa)
            .con_nombre(datos.get("nombre"))
            .con_descripcion(datos.get("descripcion", ""))
            .con_fechas(fecha_inicio, fecha_fin)
            .build()
        )

        proyecto.save()

        notificador = self.notificador_factory.crear()

        notificador.enviar_confirmacion(
            destinatario=empresa.correo,
            proyecto=proyecto,
        )

        return proyecto

    @staticmethod
    def _parse_date(value):
        if not value:
            return None

        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ProyectoInvalidoError(
                "Las fechas deben tener formato YYYY-MM-DD."
            )

    @staticmethod
    def _verificar_limite(empresa, suscripcion):
        proyectos_actuales = empresa.proyectos.count()

        if not suscripcion.verificar_limites(proyectos_actuales):
            raise LimiteSuscripcionExcedido(
                "La empresa alcanzo el limite de proyectos."
            )
