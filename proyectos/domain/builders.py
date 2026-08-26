from ..models import Proyecto, Inspeccion
from .exceptions import ProyectoInvalidoError, InspeccionInvalidaError


class ProyectoBuilder:
    """
    Patron Creacional: Builder.
    Construye un Proyecto paso a paso mediante interfaz fluida
    (Fluent Interface), garantizando que el objeto resultante sea
    valido ANTES de llamar a .save(). Vive en domain/ porque solo
    conoce reglas de negocio, no detalles de Django/infraestructura.
    """

    def __init__(self):
        self._empresa = None
        self._nombre = None
        self._descripcion = ""
        self._fecha_inicio = None
        self._fecha_fin = None

    def para_empresa(self, empresa):
        self._empresa = empresa
        return self

    def con_nombre(self, nombre):
        self._nombre = nombre
        return self

    def con_descripcion(self, descripcion):
        self._descripcion = descripcion or ""
        return self

    def con_fechas(self, fecha_inicio, fecha_fin):
        self._fecha_inicio = fecha_inicio
        self._fecha_fin = fecha_fin
        return self

    def build(self) -> Proyecto:
        self._validar()
        return Proyecto(
            empresa=self._empresa,
            nombre=self._nombre,
            descripcion=self._descripcion,
            fecha_inicio=self._fecha_inicio,
            fecha_fin=self._fecha_fin,
            estado=Proyecto.Estado.PLANEADO,
        )

    def _validar(self):
        if self._empresa is None:
            raise ProyectoInvalidoError("El proyecto requiere una empresa.")
        if not self._nombre or not self._nombre.strip():
            raise ProyectoInvalidoError("El nombre del proyecto es obligatorio.")
        if self._fecha_inicio and self._fecha_fin:
            if self._fecha_fin < self._fecha_inicio:
                raise ProyectoInvalidoError(
                    "La fecha de fin no puede ser anterior a la de inicio."
                )


class InspeccionBuilder:
    """
    Patron Creacional: Builder — ENTIDAD MAS COMPLEJA DEL SISTEMA.
    Construye una Inspeccion paso a paso mediante interfaz fluida,
    forzando el estado inicial de negocio (PENDIENTE) y validando
    consistencia contra el Proyecto padre ANTES de guardar. Vive en
    domain/ porque solo conoce reglas de negocio, no DRF ni HTTP.

    El manejo de fotografias NO ocurre aqui: ese es un detalle de
    persistencia posterior (requiere que la Inspeccion ya tenga PK)
    y por eso lo orquesta InspeccionService, no el Builder.
    """

    def __init__(self):
        self._proyecto = None
        self._inspector = None
        self._tipo_inspeccion = Inspeccion.TipoInspeccion.AVANCE_GENERAL
        self._observaciones = ""
        self._fecha_visita = None
        self._porcentaje_avance_reportado = None

    def para_proyecto(self, proyecto):
        self._proyecto = proyecto
        return self

    def por_inspector(self, inspector):
        self._inspector = inspector
        return self

    def de_tipo(self, tipo_inspeccion):
        self._tipo_inspeccion = tipo_inspeccion or Inspeccion.TipoInspeccion.AVANCE_GENERAL
        return self

    def con_observaciones(self, observaciones):
        self._observaciones = observaciones or ""
        return self

    def con_fecha_visita(self, fecha_visita):
        self._fecha_visita = fecha_visita
        return self

    def con_avance_reportado(self, porcentaje):
        self._porcentaje_avance_reportado = porcentaje
        return self

    def build(self) -> Inspeccion:
        self._validar()
        return Inspeccion(
            proyecto=self._proyecto,
            inspector=self._inspector,
            tipo_inspeccion=self._tipo_inspeccion,
            observaciones=self._observaciones,
            fecha_visita=self._fecha_visita,
            porcentaje_avance_reportado=self._porcentaje_avance_reportado,
            estado=Inspeccion.Estado.PENDIENTE,
        )

    def _validar(self):
        if self._proyecto is None:
            raise InspeccionInvalidaError("La inspeccion requiere un proyecto.")
        if self._inspector is None:
            raise InspeccionInvalidaError("La inspeccion requiere un inspector.")
        if self._fecha_visita is None:
            raise InspeccionInvalidaError("La fecha de visita es obligatoria.")
        if self._porcentaje_avance_reportado is None:
            raise InspeccionInvalidaError("El porcentaje de avance reportado es obligatorio.")
        if not (0 <= self._porcentaje_avance_reportado <= 100):
            raise InspeccionInvalidaError(
                "El porcentaje de avance reportado debe estar entre 0 y 100."
            )
        if self._proyecto.fecha_inicio and self._fecha_visita < self._proyecto.fecha_inicio:
            raise InspeccionInvalidaError(
                "La fecha de visita no puede ser anterior al inicio del proyecto."
            )