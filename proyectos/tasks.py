"""Trabajos de fondo del entregable: resumen de proyectos para descarga."""
from celery import shared_task
from django.utils import timezone
import json
import logging
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)


@shared_task(bind=True, name="proyectos.generar_reporte")
def generar_reporte(self, empresa_id):
    # Import local para que el worker inicialice Django antes de tocar modelos.
    from .models import Proyecto
    proyectos = Proyecto.objects.filter(empresa_id=empresa_id).order_by("nombre")
    filas = [{"nombre": p.nombre, "descripcion": p.descripcion,
              "ciudad": p.ciudad, "tipo": p.tipo_proyecto,
              "estado": p.get_estado_display(), "fecha_inicio": str(p.fecha_inicio or ""),
              "fecha_fin": str(p.fecha_fin or ""),
              "avance": float(p.porcentaje_avance), "riesgo": p.get_riesgo_display()}
             for p in proyectos]
    return {"generado_en": timezone.localtime().isoformat(), "total": len(filas), "proyectos": filas}


@shared_task(bind=True, name="proyectos.enviar_notificacion", max_retries=3)
def enviar_notificacion(self, url, payload):
    """Entrega notificaciones fuera del request; reintenta ante fallos temporales."""
    if self.request.is_eager:
        # La ejecución local sin worker representa el evento en consola y no
        # intenta la red; en Compose el worker realiza la integración HTTP real.
        log.info("[DEV-MOCK] Notificación preparada para %s", payload.get("destinatario"))
        return {"entregada": False, "modo": "demo-local"}
    request = Request(url, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            return {"entregada": response.status < 300}
    except Exception as exc:
        log.warning("Notificación fallida (intento %s): %s", self.request.retries + 1, exc)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
