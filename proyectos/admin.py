from django.contrib import admin
from .models import (
    Empresa,
    Usuario,
    Suscripcion,
    Proyecto,
    Inspeccion,
    Fotografia,
    RegistroBitacora,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "plan", "estado")
    search_fields = ("nombre", "nit")


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo", "empresa", "rol")
    list_filter = ("rol",)
    search_fields = ("nombre", "correo")


@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ("empresa", "plan", "fecha_inicio", "fecha_fin")
    list_filter = ("plan",)


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "empresa", "estado", "riesgo", "porcentaje_avance", "ciudad",
    )
    list_filter = ("estado", "riesgo")
    search_fields = ("nombre", "ciudad")


@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = (
        "proyecto", "tipo_inspeccion", "estado", "fecha_visita", "inspector",
    )
    list_filter = ("estado", "tipo_inspeccion")


@admin.register(Fotografia)
class FotografiaAdmin(admin.ModelAdmin):
    list_display = ("inspeccion", "categoria", "subida_en")


@admin.register(RegistroBitacora)
class RegistroBitacoraAdmin(admin.ModelAdmin):
    list_display = ("proyecto", "accion", "usuario", "creado_en")
    list_filter = ("accion",)
 
