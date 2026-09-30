"""
Microservicio de Notificaciones (Flask) - Strangler Pattern sobre Civix.

Extrae del monolito Django la responsabilidad de ENTREGAR notificaciones
(antes: proyectos/infra/notificadores.py). El monolito sigue decidiendo
QUE se dice; este servicio decide COMO se entrega.

Rutas (expuestas por Nginx bajo /api/v2/notificaciones/):
  GET  /api/v2/notificaciones/health
  POST /api/v2/notificaciones/
  GET  /api/v2/notificaciones/
  GET  /api/v2/notificaciones/<id>
"""
import logging
import os
import re
import uuid
from collections import deque
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CANALES_VALIDOS = {"email", "consola"}
PREFIJO = "/api/v2/notificaciones"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("notificaciones")


class ErrorAPI(Exception):
    """Error de negocio/validacion que se traduce a una respuesta JSON estructurada."""

    def __init__(self, status, codigo, mensaje, detalles=None):
        super().__init__(mensaje)
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or {}


def error_json(status, codigo, mensaje, detalles=None):
    return (
        jsonify({"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}}}),
        status,
    )


# ----------------------------------------------------------------------
# Logica de negocio (aislada de Flask para poder probarla facil)
# ----------------------------------------------------------------------
def validar_payload(data):
    if not isinstance(data, dict):
        raise ErrorAPI(400, "JSON_INVALIDO", "El cuerpo debe ser un objeto JSON.")

    errores = {}

    destinatario = data.get("destinatario")
    if not isinstance(destinatario, str) or not EMAIL_RE.match(destinatario.strip()):
        errores["destinatario"] = "Debe ser un correo valido."

    mensaje = data.get("mensaje")
    if not isinstance(mensaje, str) or not mensaje.strip():
        errores["mensaje"] = "Es obligatorio y no puede estar vacio."

    proyecto = data.get("proyecto")
    if not isinstance(proyecto, dict) or not str(proyecto.get("nombre", "")).strip():
        errores["proyecto.nombre"] = "Es obligatorio."

    canal = data.get("canal", "email")
    if canal not in CANALES_VALIDOS:
        errores["canal"] = f"Canal no soportado. Validos: {sorted(CANALES_VALIDOS)}."

    if errores:
        raise ErrorAPI(400, "VALIDACION_FALLIDA", "Datos de notificacion invalidos.", errores)

    return {
        "destinatario": destinatario.strip(),
        "mensaje": mensaje.strip(),
        "proyecto": {"id": str(proyecto.get("id", "")), "nombre": proyecto["nombre"].strip()},
        "canal": canal,
    }


def construir_notificacion(datos):
    return {
        "id": str(uuid.uuid4()),
        "destinatario": datos["destinatario"],
        "canal": datos["canal"],
        "asunto": f"Civix - {datos['proyecto']['nombre']}",
        "mensaje": datos["mensaje"],
        "proyecto": datos["proyecto"],
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "estado": "pendiente",
    }


def entregar(notificacion):
    """Entrega la notificacion. En ENV_TYPE=REAL aqui iria SendGrid/SMTP;
    por defecto es simulada (igual que ConsoleNotificador del monolito)."""
    etiqueta = "EMAIL" if os.environ.get("ENV_TYPE", "DEV") == "REAL" else "DEV-MOCK"
    log.info(
        "[%s] a %s | %s | %s",
        etiqueta, notificacion["destinatario"], notificacion["asunto"], notificacion["mensaje"],
    )


# ----------------------------------------------------------------------
# Aplicacion Flask
# ----------------------------------------------------------------------
def create_app():
    app = Flask(__name__)
    app.config["HISTORIAL"] = deque(maxlen=100)  # en memoria: se pierde al reiniciar

    @app.get(f"{PREFIJO}/health")
    def health():
        return jsonify({"servicio": "notificaciones", "estado": "ok"}), 200

    @app.post(f"{PREFIJO}/", strict_slashes=False)
    def crear_notificacion():
        if not request.is_json:
            raise ErrorAPI(415, "CONTENT_TYPE_INVALIDO", "Use Content-Type: application/json.")
        data = request.get_json(silent=True)
        if data is None:
            raise ErrorAPI(400, "JSON_MALFORMADO", "El cuerpo no es un JSON valido.")

        datos = validar_payload(data)
        notificacion = construir_notificacion(datos)
        entregar(notificacion)
        notificacion["estado"] = "enviada"
        app.config["HISTORIAL"].appendleft(notificacion)
        return jsonify(notificacion), 201

    @app.get(f"{PREFIJO}/", strict_slashes=False)
    def listar_notificaciones():
        return jsonify(list(app.config["HISTORIAL"])), 200

    @app.get(f"{PREFIJO}/<notificacion_id>")
    def detalle_notificacion(notificacion_id):
        for n in app.config["HISTORIAL"]:
            if n["id"] == notificacion_id:
                return jsonify(n), 200
        raise ErrorAPI(404, "NO_ENCONTRADA", "Notificacion no encontrada.")

    # ---------------- Manejo de errores (resiliencia) ----------------
    @app.errorhandler(ErrorAPI)
    def manejar_error_api(e):
        return error_json(e.status, e.codigo, e.mensaje, e.detalles)

    @app.errorhandler(HTTPException)
    def manejar_http(e):
        return error_json(e.code, e.name.upper().replace(" ", "_"), e.description)

    @app.errorhandler(Exception)
    def manejar_inesperado(e):
        log.exception("Error inesperado")
        return error_json(500, "ERROR_INTERNO", "Error interno del servicio de notificaciones.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
