from django.db import transaction
from django.utils import timezone

from ..models import Proyecto, Usuario, Inspeccion, Fotografia, RegistroBitacora
from ..domain.builders import InspeccionBuilder
from ..domain.exceptions import InspeccionInvalidaError, TransicionInvalidaError


class InspeccionService:
    """
    Capa de Aplicacion (Service Layer) para el agregado Inspeccion.
    Orquesta el flujo de negocio principal de la Entrega 1:

        crear_inspeccion()    -> Inspeccion queda en PENDIENTE
        corregir_inspeccion() -> edita datos mientras sigue PENDIENTE
        confirmar_inspeccion()-> pasa a CONFIRMADA y ACTUALIZA
                                  oficialmente Proyecto.porcentaje_avance

    Cada metodo tiene una unica responsabilidad (SRP). Todos escriben
    en RegistroBitacora (auditoria/historial del sistema).
    """

    def __init__(self, notificador):
        self.notificador = notificador

    @transaction.atomic
    def crear_inspeccion(self, proyecto_id, inspector_id, tipo_inspeccion,
                          observaciones, fecha_visita,
                          porcentaje_avance_reportado, fotografias=None):
        proyecto = Proyecto.objects.select_for_update().get(id=proyecto_id)
        inspector = Usuario.objects.get(id=inspector_id)

        inspeccion = (
            InspeccionBuilder()
            .para_proyecto(proyecto)
            .por_inspector(inspector)
            .de_tipo(tipo_inspeccion)
            .con_observaciones(observaciones)
            .con_fecha_visita(fecha_visita)
            .con_avance_reportado(porcentaje_avance_reportado)
            .build()
        )
        inspeccion.save()

        for archivo in (fotografias or []):
            Fotografia.objects.create(inspeccion=inspeccion, imagen=archivo)

        RegistroBitacora.objects.create(
            proyecto=proyecto,
            inspeccion=inspeccion,
            usuario=inspector,
            accion=RegistroBitacora.Accion.INSPECCION_CREADA,
            descripcion=(
                f"Inspección {inspeccion.get_tipo_inspeccion_display()} "
                f"registrada por {inspector.nombre}. Queda pendiente de "
                "confirmación."
            ),
        )

        return inspeccion

    @transaction.atomic
    def corregir_inspeccion(self, inspeccion_id, observaciones=None,
                             porcentaje_avance_reportado=None,
                             usuario_id=None):
        inspeccion = Inspeccion.objects.select_for_update().get(id=inspeccion_id)

        if inspeccion.estado != Inspeccion.Estado.PENDIENTE:
            raise TransicionInvalidaError(
                "Solo se pueden corregir inspecciones en estado pendiente."
            )

        if observaciones is not None:
            inspeccion.observaciones = observaciones

        if porcentaje_avance_reportado is not None:
            if not (0 <= porcentaje_avance_reportado <= 100):
                raise InspeccionInvalidaError(
                    "El porcentaje de avance reportado debe estar entre 0 y 100."
                )
            inspeccion.porcentaje_avance_reportado = porcentaje_avance_reportado

        inspeccion.save()

        actor = self._resolver_actor(usuario_id, inspeccion.inspector)
        RegistroBitacora.objects.create(
            proyecto=inspeccion.proyecto,
            inspeccion=inspeccion,
            usuario=actor,
            accion=RegistroBitacora.Accion.INSPECCION_CORREGIDA,
            descripcion="Los cambios quedan registrados en la bitácora.",
        )

        return inspeccion

    @transaction.atomic
    def confirmar_inspeccion(self, inspeccion_id, usuario_id=None):
        inspeccion = Inspeccion.objects.select_for_update().get(id=inspeccion_id)

        if inspeccion.estado != Inspeccion.Estado.PENDIENTE:
            raise TransicionInvalidaError(
                "La inspección ya fue confirmada anteriormente."
            )

        inspeccion.estado = Inspeccion.Estado.CONFIRMADA
        inspeccion.confirmada_en = timezone.now()
        inspeccion.save()

        proyecto = Proyecto.objects.select_for_update().get(id=inspeccion.proyecto_id)
        proyecto.porcentaje_avance = inspeccion.porcentaje_avance_reportado
        proyecto.save(update_fields=["porcentaje_avance"])

        actor = self._resolver_actor(usuario_id, inspeccion.inspector)

        RegistroBitacora.objects.create(
            proyecto=proyecto,
            inspeccion=inspeccion,
            usuario=actor,
            accion=RegistroBitacora.Accion.INSPECCION_CONFIRMADA,
            descripcion=f"Inspección confirmada por {actor.nombre}.",
        )
        RegistroBitacora.objects.create(
            proyecto=proyecto,
            inspeccion=inspeccion,
            usuario=actor,
            accion=RegistroBitacora.Accion.AVANCE_ACTUALIZADO,
            descripcion=f"Avance actualizado al {proyecto.porcentaje_avance}%.",
        )

        self.notificador.enviar_confirmacion(
            destinatario=proyecto.empresa.correo,
            proyecto=proyecto,
            mensaje=(
                f"La inspección de '{proyecto.nombre}' fue confirmada. "
                f"Avance oficial actualizado al {proyecto.porcentaje_avance}%."
            ),
        )

        return inspeccion

    @staticmethod
    def _resolver_actor(usuario_id, actor_por_defecto):
        if usuario_id:
            usuario = Usuario.objects.filter(id=usuario_id).first()
            if usuario:
                return usuario
        return actor_por_defecto