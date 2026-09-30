"""
Capa de Presentacion (DRF) - Serializers.

REGLA DE ARQUITECTURA (2.2 del PDF): estos serializers SOLO validan
formato, tipos de datos y presencia de campos. Ninguna regla de negocio
(limites de suscripcion, transiciones de estado, validaciones cruzadas
entre entidades) vive aqui: eso es responsabilidad exclusiva del
Builder y del Service Layer (domain/ y services/).
"""

from rest_framework import serializers

from .models import Proyecto, Inspeccion, Fotografia, RegistroBitacora, Usuario


# ---------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    """Entrada para iniciar sesion. 'dispositivo' es una etiqueta libre
    (ej. nombre del navegador/equipo) - preparacion para el concepto de
    'dispositivo autorizado' de la vision de producto, no se valida aun."""

    correo = serializers.EmailField()
    contrasena = serializers.CharField(write_only=True)
    dispositivo = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class UsuarioSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source="get_rol_display", read_only=True)
    es_gerencial = serializers.BooleanField(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "empresa", "nombre", "correo", "rol", "rol_display",
            "es_gerencial",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------
# Proyecto
# ---------------------------------------------------------------------
class ProyectoSerializer(serializers.ModelSerializer):
    """Salida (lectura) de un Proyecto. Todos los campos son solo-lectura:
    la creacion pasa por ProyectoCreateSerializer + ProyectoService, y
    porcentaje_avance solo cambia via InspeccionService.confirmar_inspeccion()."""

    class Meta:
        model = Proyecto
        fields = [
            "id", "empresa", "responsable", "nombre", "descripcion",
            "ciudad", "tipo_proyecto", "estado", "riesgo", "presupuesto",
            "porcentaje_avance", "fecha_inicio", "fecha_fin",
            "imagen_principal",
        ]
        read_only_fields = fields


class ProyectoCreateSerializer(serializers.Serializer):
    """
    Entrada para crear un Proyecto. Mantiene los nombres de campo
    originales (fechaInicio/fechaFin) que ya usaba el formulario HTML
    del taller, para no romper el frontend existente.
    """

    nombre = serializers.CharField(max_length=150)
    descripcion = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    fechaInicio = serializers.DateField(required=False, allow_null=True, default=None)
    fechaFin = serializers.DateField(required=False, allow_null=True, default=None)


# ---------------------------------------------------------------------
# Fotografia
# ---------------------------------------------------------------------
class FotografiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fotografia
        fields = ["id", "imagen", "categoria", "subida_en"]
        read_only_fields = fields


# ---------------------------------------------------------------------
# Inspeccion
# ---------------------------------------------------------------------
class InspeccionSerializer(serializers.ModelSerializer):
    """Salida (lectura) de una Inspeccion, con sus fotografias anidadas."""

    fotografias = FotografiaSerializer(many=True, read_only=True)
    inspector_nombre = serializers.CharField(
        source="inspector.nombre", read_only=True
    )
    tipo_inspeccion_display = serializers.CharField(
        source="get_tipo_inspeccion_display", read_only=True
    )
    estado_display = serializers.CharField(
        source="get_estado_display", read_only=True
    )

    class Meta:
        model = Inspeccion
        fields = [
            "id", "proyecto", "inspector", "inspector_nombre",
            "tipo_inspeccion", "tipo_inspeccion_display",
            "estado", "estado_display", "observaciones", "fecha_visita",
            "porcentaje_avance_reportado", "creado_en", "confirmada_en",
            "fotografias",
        ]
        read_only_fields = fields


class InspeccionCreateSerializer(serializers.Serializer):
    """Entrada para crear una Inspeccion. Las fotografias NO se validan
    aqui (llegan por request.FILES y se procesan en la vista) para evitar
    acoplar este serializer a los detalles de multipart/form-data."""

    usuario_id = serializers.UUIDField()
    tipo_inspeccion = serializers.ChoiceField(
        choices=Inspeccion.TipoInspeccion.choices, required=False
    )
    observaciones = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    fecha_visita = serializers.DateField()
    porcentaje_avance_reportado = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )


class InspeccionCorregirSerializer(serializers.Serializer):
    """Entrada para corregir una Inspeccion pendiente. Todos los campos
    son opcionales: solo se actualiza lo que el cliente envie."""

    usuario_id = serializers.UUIDField(required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    porcentaje_avance_reportado = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )


class InspeccionConfirmarSerializer(serializers.Serializer):
    """Entrada para confirmar una Inspeccion. usuario_id es opcional:
    si no se envia, se usa el inspector original como actor."""

    usuario_id = serializers.UUIDField(required=False)


# ---------------------------------------------------------------------
# RegistroBitacora
# ---------------------------------------------------------------------
class RegistroBitacoraSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.nombre", read_only=True, default=None
    )
    accion_display = serializers.CharField(
        source="get_accion_display", read_only=True
    )

    class Meta:
        model = RegistroBitacora
        fields = [
            "id", "proyecto", "inspeccion", "usuario", "usuario_nombre",
            "accion", "accion_display", "descripcion", "creado_en",
        ]
        read_only_fields = fields
