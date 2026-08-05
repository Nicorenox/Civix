from django.contrib import admin
from .models import Empresa, Usuario, Suscripcion, Proyecto

admin.site.register(Empresa)
admin.site.register(Usuario)
admin.site.register(Suscripcion)
admin.site.register(Proyecto)
