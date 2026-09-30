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
        # Aqui iria la integracion real, ej:
        # sendgrid_client.send(to=destinatario, template="notificacion_civix", ...)
        print(
            f"[EMAIL] Enviando a {destinatario} sobre '{proyecto.nombre}': {mensaje}"
        )


class ConsoleNotificador(Notificador):
    """Implementacion simulada (MOCK), usada en desarrollo/pruebas."""

    def enviar_confirmacion(self, destinatario, proyecto, mensaje):
        print(
            f"[DEV-MOCK] Notificacion a {destinatario} sobre '{proyecto.nombre}': {mensaje}"
        )


class HttpNotificador(Notificador):
    """
    Strangler Pattern: delega la entrega al microservicio Flask de
    Notificaciones por HTTP/JSON. Es una tercera implementacion del mismo
    contrato `Notificador`, asi que ningun Service ni vista cambia (DIP).

    Resiliencia: si el microservicio no responde, NO se rompe el caso de
    uso del monolito (crear proyecto / confirmar inspeccion); se registra
    el fallo y se cae al mock por consola.
    """

    def __init__(self, url=None, timeout=3):
        import os

        self.url = url or os.environ.get(
            "NOTIFICACIONES_URL",
            "http://flask_notificaciones:5000/api/v2/notificaciones/",
        )
        self.timeout = timeout

    def enviar_confirmacion(self, destinatario, proyecto, mensaje):
        import json
        import logging
        import urllib.request

        payload = json.dumps(
            {
                "destinatario": destinatario,
                "mensaje": mensaje,
                "proyecto": {"id": str(proyecto.id), "nombre": proyecto.nombre},
                "canal": "email",
            }
        ).encode("utf-8")
        peticion = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self.timeout):
                pass
        except Exception as exc:  # timeout, conexion rechazada, 4xx/5xx
            logging.getLogger(__name__).warning(
                "Microservicio de notificaciones no disponible (%s). Uso fallback.", exc
            )
            ConsoleNotificador().enviar_confirmacion(destinatario, proyecto, mensaje)
