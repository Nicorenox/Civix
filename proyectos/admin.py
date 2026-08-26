from django import forms
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


class UsuarioAdminForm(forms.ModelForm):
    """
    Reemplaza el campo crudo `contrasena_hash` por un campo de texto plano
    llamado `contrasena`. Nunca se muestra ni se guarda el hash existente
    en el formulario: se deja en blanco y solo se actualiza si el
    administrador escribe algo nuevo (igual que hace UserAdmin de Django).
    """

    contrasena = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput,
        help_text=(
            "Escribe una contraseña para crear el usuario o cambiarla. "
            "Déjala en blanco al editar si no quieres modificarla."
        ),
    )

    class Meta:
        model = Usuario
        exclude = ("contrasena_hash",)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        nueva_contrasena = self.cleaned_data.get("contrasena")
        if nueva_contrasena:
            usuario.set_password(nueva_contrasena)
        elif not usuario.contrasena_hash:
            # Usuario nuevo sin contraseña escrita: evita guardarlo
            # con contrasena_hash vacío (no podría iniciar sesión nunca).
            raise forms.ValidationError(
                "Debes escribir una contraseña para crear el usuario."
            )
        if commit:
            usuario.save()
        return usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioAdminForm
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
