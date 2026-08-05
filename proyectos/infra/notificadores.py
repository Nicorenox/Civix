from abc import ABC, abstractmethod


class Notificador(ABC):
    """
    Contrato (interfaz) que la capa de Aplicacion conoce.
    Permite DIP: el Service depende de esta abstraccion, no de una
    implementacion concreta.
    """

    @abstractmethod
    def enviar_confirmacion(self, destinatario, proyecto):
        ...


class EmailNotificador(Notificador):
    """Implementacion REAL, usando un proveedor externo (ej. SendGrid)."""

    def enviar_confirmacion(self, destinatario, proyecto):
        # Aqui iria la integracion real, ej:
        # sendgrid_client.send(to=destinatario, template="proyecto_creado", ...)
        print(
            f"[EMAIL] Enviando confirmacion real a {destinatario} "
            f"por el proyecto '{proyecto.nombre}'"
        )


class ConsoleNotificador(Notificador):
    """Implementacion simulada (MOCK), usada en desarrollo/pruebas."""

    def enviar_confirmacion(self, destinatario, proyecto):
        print(
            f"[DEV-MOCK] Notificacion simulada a {destinatario}: "
            f"proyecto '{proyecto.nombre}' creado."
        )
