from datetime import date
from django.test import TestCase
from django.urls import reverse

from .models import Empresa, Suscripcion, Proyecto


class CrearProyectoTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Demo",
            nit="900123456-7",
            correo="demo@civix.test",
        )
        Suscripcion.objects.create(
            empresa=self.empresa,
            plan=Suscripcion.TipoPlan.BASICO,
            fecha_inicio=date.today(),
            fecha_fin=date(2030, 12, 31),
        )

    def test_pagina_html_se_renderiza(self):
        url = reverse("crear_proyecto_page", kwargs={"empresa_id": self.empresa.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear proyecto")
        self.assertContains(response, self.empresa.nombre)

    def test_crear_proyecto_desde_api(self):
        url = reverse("crear_proyecto", kwargs={"empresa_id": self.empresa.id})
        response = self.client.post(
            url,
            data={
                "nombre": "Proyecto Civix",
                "descripcion": "Proyecto de prueba",
                "fechaInicio": "2026-08-05",
                "fechaFin": "2026-12-31",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Proyecto.objects.count(), 1)
        self.assertEqual(Proyecto.objects.first().nombre, "Proyecto Civix")

    def test_rechaza_fecha_fin_anterior(self):
        url = reverse("crear_proyecto", kwargs={"empresa_id": self.empresa.id})
        response = self.client.post(
            url,
            data={
                "nombre": "Proyecto inválido",
                "fechaInicio": "2026-12-31",
                "fechaFin": "2026-01-01",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Proyecto.objects.count(), 0)
