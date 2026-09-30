class ProyectoInvalidoError(Exception):
    """Se lanza cuando el Builder no puede construir un Proyecto valido."""
    pass


class LimiteSuscripcionExcedido(Exception):
    """Se lanza cuando la Empresa excede los limites de su plan."""
    pass


class InspeccionInvalidaError(Exception):
    """Se lanza cuando el InspeccionBuilder no puede construir una
    Inspeccion valida (datos faltantes o inconsistentes)."""
    pass


class TransicionInvalidaError(Exception):
    """
    Se lanza cuando se intenta una transicion de estado no permitida sobre
    una Inspeccion (ej. confirmar una inspeccion que ya fue confirmada, o
    corregir una que ya no esta pendiente). Es un CONFLICTO de negocio,
    no un error de validacion de datos -> la vista debe traducirlo a
    HTTP 409, no a 400.
    """
    pass


class CredencialesInvalidasError(Exception):
    """
    Se lanza cuando el login falla (correo no existe o contrasena
    incorrecta). Se traduce a HTTP 401 (no 400): el formato de la
    peticion es correcto, lo que falla es la identidad presentada.
    """
    pass
