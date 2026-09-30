import secrets
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import MaxValueValidator, MinValueValidator
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
        # Experiencia "gerencial / visualizador" descrita en la vision del
        # producto (vs. los 3 roles anteriores, que son "operativos").
        GERENTE = "gerente", "Gerente"

    ROLES_OPERATIVOS = {Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.COLABORADOR}

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
    # PREPARADO PARA SEGURIDAD FUTURA (no forzado todavia, ver AuthService
    # y proyectos/infra/authentication.py): si en el futuro se activa 2FA,
    # este flag decide que usuarios deben completar el segundo factor.
    dos_fa_habilitado = models.BooleanField(default=False)

    def set_password(self, raw_password):
        """Hashea y guarda la contrasena (nunca se persiste en texto plano).
        Usa los mismos hashers que Django (PBKDF2), es persistencia segura,
        no logica de negocio."""
        self.contrasena_hash = make_password(raw_password)

    def check_password(self, raw_password) -> bool:
        return check_password(raw_password, self.contrasena_hash)

    @property
    def es_gerencial(self) -> bool:
        return self.rol == self.Rol.GERENTE

    @property
    def is_authenticated(self) -> bool:
        """Contrato esperado por DRF (permissions.IsAuthenticated) y por
        Django en general: si existe la instancia, esta autenticado."""
        return True

    def __str__(self):
        return self.nombre


class SesionToken(models.Model):
    """
    Token de acceso simple emitido al iniciar sesion. Representa tambien
    (de forma preparatoria) el concepto de "dispositivo autorizado" de la
    vision del producto: cada SesionToken queda asociado a una etiqueta de
    dispositivo. NO implementa mTLS ni 2FA todavia (ver AuthService) - es
    la base sobre la que esas validaciones se conectarian mas adelante.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="sesiones"
    )
    token = models.CharField(max_length=64, unique=True, editable=False)
    dispositivo = models.CharField(max_length=150, blank=True, default="")
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        estado = "activa" if self.activo else "inactiva"
        return f"Sesion de {self.usuario.nombre} ({estado})"


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

    class Riesgo(models.TextChoices):
        BAJO = "bajo", "Bajo"
        MEDIO = "medio", "Medio"
        ALTO = "alto", "Alto"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="proyectos"
    )
    responsable = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name="proyectos_a_cargo",
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, default="")
    ciudad = models.CharField(max_length=100, blank=True, default="")
    tipo_proyecto = models.CharField(max_length=100, blank=True, default="")
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PLANEADO
    )
    riesgo = models.CharField(
        max_length=10, choices=Riesgo.choices, default=Riesgo.BAJO
    )
    presupuesto = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    # Solo se actualiza a traves de InspeccionService.confirmar_inspeccion().
    # Ningun serializer/endpoint de "editar proyecto" debe exponer este
    # campo como escribible directamente: ver PASO 5 (Service Layer).
    porcentaje_avance = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    imagen_principal = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.nombre


class Inspeccion(models.Model):
    """
    Entidad central del flujo operativo. Representa una visita de obra
    registrada por un inspector. NO actualiza el Proyecto directamente:
    queda en estado PENDIENTE hasta que InspeccionService.confirmar_inspeccion()
    la valida y la confirma (ver PASO 5 - Service Layer).
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        CONFIRMADA = "confirmada", "Confirmada"

    class TipoInspeccion(models.TextChoices):
        AVANCE_GENERAL = "avance_general", "Avance general"
        ESTRUCTURA = "estructura", "Estructura"
        FACHADA_ACABADOS = "fachada_acabados", "Fachada y acabados"
        INSTALACIONES = "instalaciones", "Instalaciones"
        OTRO = "otro", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="inspecciones"
    )
    inspector = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="inspecciones_realizadas"
    )
    tipo_inspeccion = models.CharField(
        max_length=30,
        choices=TipoInspeccion.choices,
        default=TipoInspeccion.AVANCE_GENERAL,
    )
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PENDIENTE
    )
    observaciones = models.TextField(blank=True, default="")
    fecha_visita = models.DateField()
    # Avance que el inspector reporta en campo. Se vuelve oficial
    # (Proyecto.porcentaje_avance) unicamente al confirmar la inspeccion.
    porcentaje_avance_reportado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_tipo_inspeccion_display()} - {self.proyecto.nombre}"


class Fotografia(models.Model):
    """Evidencia fotografica asociada a una Inspeccion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspeccion = models.ForeignKey(
        Inspeccion, on_delete=models.CASCADE, related_name="fotografias"
    )
    imagen = models.ImageField(upload_to="inspecciones/%Y/%m/")
    categoria = models.CharField(max_length=50, blank=True, default="")
    subida_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto {self.id} - {self.inspeccion_id}"


class RegistroBitacora(models.Model):
    """
    Auditoria de cambios (bitacora). Cada accion relevante del flujo de
    inspeccion escribe aqui un registro inmutable. Esta es la entidad
    que alimenta las pantallas de "Actividad reciente" / "Bitacora de
    inspecciones" de los mockups. Solo el Service Layer debe crear
    registros aqui (nunca directamente desde una vista).
    """

    class Accion(models.TextChoices):
        INSPECCION_CREADA = "inspeccion_creada", "Inspección creada"
        INSPECCION_CORREGIDA = "inspeccion_corregida", "Inspección corregida"
        INSPECCION_CONFIRMADA = "inspeccion_confirmada", "Inspección confirmada"
        AVANCE_ACTUALIZADO = "avance_actualizado", "Avance actualizado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, related_name="bitacora"
    )
    inspeccion = models.ForeignKey(
        Inspeccion,
        on_delete=models.SET_NULL,
        related_name="registros_bitacora",
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name="acciones_registradas",
        null=True,
        blank=True,
    )
    accion = models.CharField(max_length=30, choices=Accion.choices)
    descripcion = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.get_accion_display()} - {self.proyecto.nombre}"
