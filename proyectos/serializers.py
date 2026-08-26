from rest_framework import serializers
from .models import Proyecto, Inspeccion, RegistroBitacora, Usuario

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
        
class ProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proyecto
        fields = "__all__"
        read_only_fields = ["id", "porcentaje_avance"]


class ProyectoCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")
    fechaInicio = serializers.DateField(required=False, allow_null=True)
    fechaFin = serializers.DateField(required=False, allow_null=True)


class InspeccionSerializer(serializers.ModelSerializer):
    fotografias = serializers.SerializerMethodField()

    class Meta:
        model = Inspeccion
        fields = "__all__"
        read_only_fields = ["id", "creado_en", "confirmada_en"]

    def get_fotografias(self, obj):
        if hasattr(obj, "fotografias"):
            fotos = obj.fotografias
            if hasattr(fotos, "all"):
                return [
                    {
                        "id": str(f.id) if hasattr(f, "id") else str(index),
                        "url": getattr(f, "url", str(f)),
                    }
                    for index, f in enumerate(fotos.all())
                ]
            if isinstance(fotos, list):
                return fotos
        return []


class InspeccionCreateSerializer(serializers.Serializer):
    usuario_id = serializers.UUIDField()
    tipo_inspeccion = serializers.CharField(required=False, default="avance_general")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    fecha_visita = serializers.DateField()
    porcentaje_avance_reportado = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )


class InspeccionCorregirSerializer(serializers.Serializer):
    usuario_id = serializers.UUIDField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    porcentaje_avance_reportado = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )


class InspeccionConfirmarSerializer(serializers.Serializer):
    usuario_id = serializers.UUIDField(required=False, allow_null=True)


class RegistroBitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroBitacora
        fields = "__all__"