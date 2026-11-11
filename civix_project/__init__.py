"""Carga Celery al iniciar Django, manteniendo la app web desacoplada."""
from .celery import app as celery_app

__all__ = ("celery_app",)
