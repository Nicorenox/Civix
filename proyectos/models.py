import uuid

from django.db import models


class Empresa(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        SUSPENDIDA = "suspendida", "Suspendida"
        CANCELADA = "cancelada", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150)
    nit = models.CharField(max_length=30, unique=True)
    correo = models.EmailField()
    plan = models.CharField(max_length=50, default="basico")
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ACTIVA
    )

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        SUPERVISOR = "supervisor", "Supervisor"
        COLABORADOR = "colaborador", "Colaborador"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="usuarios"
    )
    nombre = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    contrasena_hash = models.CharField(max_length=255)
    rol = models.CharField(
        max_length=20, choices=Rol.choices, default=Rol.COLABORADOR
    )

    def __str__(self):
        return self.nombre


class Suscripcion(models.Model):
    class TipoPlan(models.TextChoices):
        BASICO = "basico", "Básico"
        PROFESIONAL = "profesional", "Profesional"
        EMPRESARIAL = "empresarial", "Empresarial"

    # Límite de proyectos activos por tipo de plan (regla de negocio simple).
    LIMITES_PROYECTOS = {
        TipoPlan.BASICO: 3,
        TipoPlan.PROFESIONAL: 15,
        TipoPlan.EMPRESARIAL: 100,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.OneToOneField(
        Empresa, on_delete=models.CASCADE, related_name="suscripcion"
    )
    plan = models.CharField(
        max_length=20, choices=TipoPlan.choices, default=TipoPlan.BASICO
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    almacenamiento_gb = models.IntegerField(default=5)

    def verificar_limites(self, proyectos_actuales: int) -> bool:
        """Responde si la empresa aun puede crear un proyecto mas."""
        limite = self.LIMITES_PROYECTOS.get(self.plan, 3)
        return proyectos_actuales < limite

    def __str__(self):
        return f"{self.empresa.nombre} - {self.plan}"


class Proyecto(models.Model):
    class Estado(models.TextChoices):
        PLANEADO = "planeado", "Planeado"
        EN_EJECUCION = "en_ejecucion", "En ejecucion"
        FINALIZADO = "finalizado", "Finalizado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="proyectos"
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, default="")
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PLANEADO
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    imagen_principal = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.nombre
