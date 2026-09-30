from django.db import transaction

from ..models import Usuario, SesionToken
from ..domain.exceptions import CredencialesInvalidasError


class AuthService:
    """
    Capa de Aplicacion para autenticacion.

    ESTADO ACTUAL (Entrega 1 + este paso adicional): valida correo y
    contrasena, y emite un SesionToken. NO exige 2FA ni certificado mTLS
    todavia -> cualquier endpoint sigue siendo accesible sin este token
    mientras su vista use el permiso por defecto (AllowAny, ver
    settings.py). Es autenticacion PREPARADA, no FORZADA.

    COMO ACTIVAR SEGURIDAD ADICIONAL MAS ADELANTE (sin romper nada):
      - 2FA: en iniciar_sesion(), si usuario.dos_fa_habilitado es True,
        en vez de emitir el SesionToken de una vez, se devolveria un
        estado intermedio "requiere_2fa" y un segundo metodo
        confirmar_2fa(usuario_id, codigo) emitiria el SesionToken.
      - mTLS / dispositivo autorizado: SesionToken.dispositivo ya
        guarda una etiqueta del dispositivo; para exigir mTLS real,
        TokenAccesoAuthentication (infra/authentication.py) validaria
        el certificado de cliente (request.META) antes de aceptar el
        token, y solo entonces se marcaria SesionToken como "confiable".
      - Para EXIGIR el token en cualquier vista: agregar
        `permission_classes = [IsAuthenticated]` a esa vista (ver
        MeAPIView como ejemplo ya activado), o cambiar
        DEFAULT_PERMISSION_CLASSES en settings.py para exigirlo en todo
        el sistema de una vez.
    """

    @transaction.atomic
    def iniciar_sesion(self, correo, contrasena, dispositivo=""):
        try:
            usuario = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            raise CredencialesInvalidasError("Correo o contraseña incorrectos.")

        if not usuario.check_password(contrasena):
            raise CredencialesInvalidasError("Correo o contraseña incorrectos.")

        # Punto de extension 2FA: ver docstring de la clase.

        sesion = SesionToken.objects.create(usuario=usuario, dispositivo=dispositivo)
        return usuario, sesion

    def cerrar_sesion(self, token):
        SesionToken.objects.filter(token=token, activo=True).update(activo=False)

    def usuario_desde_token(self, token):
        sesion = (
            SesionToken.objects.filter(token=token, activo=True)
            .select_related("usuario")
            .first()
        )
        if not sesion:
            return None
        return sesion.usuario
