from django.db import transaction

from ..models import Empresa, Suscripcion
from ..domain.builders import ProyectoBuilder
from ..domain.exceptions import LimiteSuscripcionExcedido


class ProyectoService:
    """
    Capa de Aplicacion (Service Layer).
    Contiene el algoritmo del caso de uso "Crear Proyecto":
      1. Valida reglas de negocio (limites de la Suscripcion).
      2. Usa el Builder para construir un Proyecto valido.
      3. Persiste y notifica a traves de una dependencia inyectada.

    Cumple DIP (Dependency Inversion Principle): depende de la
    abstraccion `Notificador`, nunca de una implementacion concreta.
    """

    def __init__(self, notificador):
        self.notificador = notificador

    @transaction.atomic
    def crear_proyecto(self, empresa_id, nombre, descripcion,
                        fecha_inicio, fecha_fin):
        empresa = Empresa.objects.select_for_update().get(id=empresa_id)
        suscripcion = Suscripcion.objects.get(empresa=empresa)

        # Regla de negocio: la Suscripcion controla los limites del plan.
        proyectos_actuales = empresa.proyectos.count()
        if not suscripcion.verificar_limites(proyectos_actuales):
            raise LimiteSuscripcionExcedido(
                "La empresa alcanzo el limite de proyectos de su plan."
            )

        # El Builder garantiza que el objeto sea valido antes de guardarlo.
        proyecto = (
            ProyectoBuilder()
            .para_empresa(empresa)
            .con_nombre(nombre)
            .con_descripcion(descripcion)
            .con_fechas(fecha_inicio, fecha_fin)
            .build()
        )
        proyecto.save()

        self.notificador.enviar_confirmacion(
            destinatario=empresa.correo,
            proyecto=proyecto,
            mensaje=f"El proyecto '{proyecto.nombre}' fue creado exitosamente.",
        )

        return proyecto
