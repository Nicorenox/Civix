from ..models import Proyecto
from .exceptions import ProyectoInvalidoError


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
