"""Adapters para integrar APIs externas detrás de contratos propios (DIP).

El dominio y las vistas no dependen del formato HTTP del tercero. Una URL
vacía o un proveedor caído devuelve una respuesta de demostración explícita.
"""
import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

log = logging.getLogger(__name__)


class JsonHttpAdapter:
    """Convierte una API JSON HTTP en el contrato pequeño usado por Civix."""
    def __init__(self, base_url, timeout=4):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path=""):
        if not self.base_url:
            return None
        request = Request(f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url,
                          headers={"Accept": "application/json", "User-Agent": "Civix/2.0"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError) as exc:
            log.warning("API externa no disponible: %s", exc)
            return None


class AliadoApiAdapter(JsonHttpAdapter):
    """Adapta el endpoint informativo aliado/demo a una tarjeta de Civix."""
    def obtener_resumen(self):
        datos = self.get()
        if not isinstance(datos, dict):
            # El entregable académico no tiene endpoint ni datos reales del
            # aliado; esta fixture demuestra la integración sin presentarse
            # como información recibida desde otro equipo.
            return {"disponible": False, "modo_demo": True, "origen": "demo",
                    "mensaje": "Datos simulados de demostración.",
                    "datos": {"proyecto": "Parque Central (demo)", "avance": 62,
                              "estado": "en ejecución", "actualizado": "2026-11-08"}}
        return {"disponible": True, "modo_demo": bool(datos.get("demo")),
                "origen": "aliado-demo" if datos.get("demo") else "aliado",
                "datos": datos}


class TercerosAdapter(JsonHttpAdapter):
    """Normaliza una API pública de terceros con timeout y fallback seguro."""
    def obtener_referencia(self):
        datos = self.get()
        if datos is None:
            return {"disponible": False, "origen": "demo", "mensaje": "Configura THIRD_PARTY_API_URL con un endpoint JSON público."}
        # El proveedor meteorológico devuelve sus valores dentro de `current`;
        # este Adapter conserva la respuesta íntegra para que la interfaz pueda
        # representar tanto este proveedor de prueba como otra API compatible.
        return {"disponible": True, "origen": "tercero", "proveedor": "Open-Meteo",
                "datos": datos}


def aliado_adapter():
    return AliadoApiAdapter(settings.PARTNER_API_URL)


def terceros_adapter():
    url = settings.THIRD_PARTY_API_URL or (
        "https://api.open-meteo.com/v1/forecast?latitude=4.7110&longitude=-74.0721"
        "&current=temperature_2m,precipitation,wind_speed_10m&timezone=America%2FBogota"
    )
    return TercerosAdapter(url)
