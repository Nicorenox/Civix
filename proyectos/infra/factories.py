import os

from .notificadores import EmailNotificador, ConsoleNotificador


class NotificadorFactory:
    """
    Patron Creacional: Factory.
    Decide, en tiempo de ejecucion, que implementacion de Notificador
    entregar segun la variable de entorno ENV_TYPE. El Service que la
    consume nunca sabe (ni le importa) cual implementacion recibio.

    Uso:
      ENV_TYPE=REAL  -> EmailNotificador   (produccion)
      ENV_TYPE=DEV   -> ConsoleNotificador (por defecto)
    """

    @staticmethod
    def crear():
        env_type = os.environ.get("ENV_TYPE", "DEV")

        if env_type == "REAL":
            return EmailNotificador()
        return ConsoleNotificador()
