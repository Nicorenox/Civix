"""Microservicio Civix de suscripciones.

Es dueño del catálogo visible y de la orquestación del checkout de demostración.
La provisión de Empresa/Usuario/Suscripción se solicita al backend de Civix por
un endpoint interno autenticado. Esta pasarela nunca recoge tarjeta ni cobra.
"""
import json
import logging
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

PREFIX = "/api/v2/suscripciones"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NIT_RE = re.compile(r"^[0-9.\-]{5,30}$")
PASSWORD_MIN = 8
LOG = logging.getLogger("suscripciones")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Los límites reflejan Suscripcion.TipoPlan y LIMITES_PROYECTOS en Django.
# El catálogo se entrega por API para que la página no invente capacidades.
PLANES = {
    "basico": {"nombre": "Esencial", "proyectos": 3, "almacenamiento_gb": 5,
               "reportes": False, "gerencial": False},
    "profesional": {"nombre": "Equipo", "proyectos": 15, "almacenamiento_gb": 15,
                    "reportes": True, "gerencial": False},
    "empresarial": {"nombre": "Institucional", "proyectos": 100, "almacenamiento_gb": 100,
                     "reportes": True, "gerencial": True},
}


def crear_app():
    app = Flask(__name__)

    @app.get(f"{PREFIX}/health")
    def health():
        return jsonify({"servicio": "suscripciones", "estado": "ok"}), 200

    @app.get(f"{PREFIX}/planes/")
    def listar_planes():
        return jsonify([{"codigo": codigo, **datos} for codigo, datos in PLANES.items()]), 200

    @app.post(f"{PREFIX}/checkout/")
    def checkout_demo():
        """Orquesta el alta del espacio y activa un plan sin procesar pagos."""
        if not request.is_json:
            return jsonify({"error": "El cuerpo debe usar application/json."}), 415
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "El cuerpo JSON no es válido."}), 400

        plan = str(datos.get("plan", "")).strip().lower()
        nombre_empresa = str(datos.get("empresa", "")).strip()
        nit = str(datos.get("nit", "")).strip()
        correo_empresa = str(datos.get("correo_empresa", "")).strip().lower()
        nombre_usuario = str(datos.get("nombre_usuario", "")).strip()
        correo_usuario = str(datos.get("correo_usuario", "")).strip().lower()
        contrasena = datos.get("contrasena", "")

        errores = {}
        if plan not in PLANES:
            errores["plan"] = "Selecciona un plan disponible."
        if len(nombre_empresa) < 2 or len(nombre_empresa) > 150:
            errores["empresa"] = "Indica el nombre de la empresa (2 a 150 caracteres)."
        if not NIT_RE.fullmatch(nit):
            errores["nit"] = "El NIT debe contener entre 5 y 30 números, puntos o guiones."
        if not EMAIL_RE.fullmatch(correo_empresa):
            errores["correo_empresa"] = "Indica un correo empresarial válido."
        if len(nombre_usuario) < 2 or len(nombre_usuario) > 150:
            errores["nombre_usuario"] = "Indica el nombre del administrador."
        if not EMAIL_RE.fullmatch(correo_usuario):
            errores["correo_usuario"] = "Indica un correo válido para iniciar sesión."
        if not isinstance(contrasena, str) or len(contrasena) < PASSWORD_MIN:
            errores["contrasena"] = f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres."
        if errores:
            return jsonify({"error": "Revisa los datos del formulario.", "detalles": errores}), 400

        service_token = os.environ.get("DEMO_PROVISION_TOKEN", "")
        provision_url = os.environ.get(
            "CIVIX_PROVISION_URL", "http://django_web:8000/api/internal/demo/provision/"
        )
        # Falla de forma cerrada: no permite altas sin autenticación entre servicios.
        if len(service_token) < 32:
            LOG.error("DEMO_PROVISION_TOKEN no está configurado correctamente.")
            return jsonify({"error": "El alta de suscripción no está configurada."}), 503

        payload = {
            "plan": plan, "empresa": nombre_empresa, "nit": nit,
            "correo_empresa": correo_empresa, "nombre_usuario": nombre_usuario,
            "correo_usuario": correo_usuario, "contrasena": contrasena,
        }
        req = Request(
            provision_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Civix-Service-Token": service_token,
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=8) as response:
                creado = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                error = json.loads(exc.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                error = {"error": "No se pudo completar el alta."}
            if exc.code in (400, 409):
                return jsonify(error), exc.code
            LOG.warning("Servicio interno respondió HTTP %s.", exc.code)
            return jsonify({"error": "No fue posible activar el plan de demostración."}), 502
        except (URLError, TimeoutError, ValueError, UnicodeDecodeError) as exc:
            LOG.warning("Provisión no disponible temporalmente: %s", exc)
            return jsonify({"error": "No fue posible conectar con el servicio de cuentas."}), 503

        # Comprobante sin cobro: no se reciben tarjetas ni se conecta una pasarela real.
        return jsonify({
            "estado": "activa_demo",
            "mensaje": "Tu espacio Civix quedó creado. No se realizó ningún cobro.",
            "pago": {"modo": "demostracion", "estado": "sin_cobro", "total": 0, "moneda": "COP"},
            "cuenta": creado,
        }), 201

    @app.errorhandler(HTTPException)
    def error_http(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def error_interno(error):
        LOG.exception("Error no controlado en suscripciones")
        return jsonify({"error": "Error interno del servicio de suscripciones."}), 500

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
