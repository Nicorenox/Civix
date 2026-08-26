from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from ..services.auth_service import AuthService


class TokenAccesoAuthentication(BaseAuthentication):
    """
    Autenticacion por token simple (cabecera 'Authorization: Token <token>').

    PREPARADA pero NO forzada: esta clase esta registrada en
    DEFAULT_AUTHENTICATION_CLASSES (settings.py), asi que SIEMPRE que
    llegue un token valido, request.user quedara poblado con el Usuario
    correspondiente. Pero como DEFAULT_PERMISSION_CLASSES sigue siendo
    AllowAny, ninguna vista exige ese token todavia -> el sistema sigue
    siendo utilizable sin login (requisito del taller).

    Para ACTIVAR la exigencia en una vista puntual, basta con declarar
    `permission_classes = [IsAuthenticated]` en esa vista (ver MeAPIView).
    """

    keyword = "Token"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None

        token = header[len(self.keyword) + 1:].strip()
        usuario = AuthService().usuario_desde_token(token)
        if usuario is None:
            raise AuthenticationFailed("Token invalido o expirado.")

        return (usuario, token)

    def authenticate_header(self, request):
        # Necesario para que DRF responda 401 (No autenticado) en vez de
        # 403 (Prohibido) cuando falta el token en una vista protegida.
        return self.keyword