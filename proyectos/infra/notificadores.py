from abc import ABC, abstractmethod


class Notificador(ABC):
    """
    Contrato (interfaz) que la capa de Aplicacion conoce.
    Permite DIP: el Service depende de esta abstraccion, no de una
    implementacion concreta. El parametro 'mensaje' lo decide quien
    llama (el Service, que conoce el contexto real del evento) - el
    Notificador solo sabe COMO entregarlo, nunca QUE dice.
    """

    @abstractmethod
    def enviar_confirmacion(self, destinatario, proyecto, mensaje):
        ...


class EmailNotificador(Notificador):
    """Implementacion REAL, usando un proveedor externo (ej. SendGrid)."""

    def enviar_confirmacion(self, destinatario, proyecto, mensaje):
        print(
            f"[EMAIL] Enviando a {destinatario} sobre '{proyecto.nombre}': {mensaje}"
        )


class ConsoleNotificador(Notificador):
    """Implementacion simulada (MOCK), usada en desarrollo/pruebas."""

    def enviar_confirmacion(self, destinatario, proyecto, mensaje):
        print(
            f"[DEV-MOCK] Notificacion a {destinatario} sobre '{proyecto.nombre}': {mensaje}"
        )