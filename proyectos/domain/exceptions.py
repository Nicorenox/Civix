class ProyectoInvalidoError(Exception):
    """Se lanza cuando el Builder no puede construir un Proyecto valido."""
    pass


class LimiteSuscripcionExcedido(Exception):
    """Se lanza cuando la Empresa excede los limites de su plan."""
    pass
