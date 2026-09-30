from datetime import date
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Empresa, Suscripcion, Usuario, Proyecto, Inspeccion, RegistroBitacora


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


def _imagen_de_prueba(nombre="foto.png"):
    """Genera un PNG minimo valido en memoria (Django ImageField exige
    que el contenido sea una imagen real, no basta con bytes cualquiera)."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(nombre, buffer.read(), content_type="image/png")


class InspeccionFlowTests(TestCase):
    """
    Cubre el flujo de negocio central de la Entrega 1:
    crear -> pendiente -> corregir -> confirmar -> actualiza proyecto.
    """

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Archetype Co.", nit="900999888-1", correo="empresa@civix.test"
        )
        Suscripcion.objects.create(
            empresa=self.empresa,
            plan=Suscripcion.TipoPlan.PROFESIONAL,
            fecha_inicio=date.today(),
            fecha_fin=date(2030, 12, 31),
        )
        self.inspector = Usuario.objects.create(
            empresa=self.empresa,
            nombre="Julián Cortés",
            correo="julian@civix.test",
            contrasena_hash="x",
            rol=Usuario.Rol.COLABORADOR,
        )
        self.proyecto = Proyecto.objects.create(
            empresa=self.empresa,
            nombre="Torre Aurora",
            fecha_inicio=date(2026, 1, 1),
        )

    def _crear_inspeccion(self, avance="74", fecha_visita="2026-08-22", **extra):
        url = reverse(
            "crear_inspeccion", kwargs={"proyecto_id": self.proyecto.id}
        )
        data = {
            "usuario_id": str(self.inspector.id),
            "tipo_inspeccion": "avance_general",
            "observaciones": "Avance dentro de lo previsto.",
            "fecha_visita": fecha_visita,
            "porcentaje_avance_reportado": avance,
        }
        data.update(extra)
        return self.client.post(url, data=data)

    def test_crear_inspeccion_queda_pendiente_y_no_actualiza_proyecto(self):
        response = self._crear_inspeccion()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["estado"], "pendiente")

        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.porcentaje_avance, 0)

    def test_crear_inspeccion_con_fotografia_real(self):
        response = self._crear_inspeccion(fotografias=[_imagen_de_prueba()])

        self.assertEqual(response.status_code, 201)
        cuerpo = response.json()
        self.assertEqual(len(cuerpo["fotografias"]), 1)

    def test_crear_inspeccion_fecha_antes_de_inicio_proyecto_devuelve_400(self):
        response = self._crear_inspeccion(fecha_visita="2025-01-01")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Inspeccion.objects.count(), 0)

    def test_confirmar_inspeccion_actualiza_avance_del_proyecto(self):
        creada = self._crear_inspeccion(avance="74").json()

        url_confirmar = reverse(
            "confirmar_inspeccion", kwargs={"inspeccion_id": creada["id"]}
        )
        response = self.client.post(
            url_confirmar,
            data={"usuario_id": str(self.inspector.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado"], "confirmada")

        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.porcentaje_avance, 74)

        self.assertEqual(
            RegistroBitacora.objects.filter(proyecto=self.proyecto).count(), 3
        )

    def test_confirmar_inspeccion_dos_veces_devuelve_409(self):
        creada = self._crear_inspeccion().json()
        url_confirmar = reverse(
            "confirmar_inspeccion", kwargs={"inspeccion_id": creada["id"]}
        )

        primera = self.client.post(
            url_confirmar,
            data={"usuario_id": str(self.inspector.id)},
            content_type="application/json",
        )
        segunda = self.client.post(
            url_confirmar,
            data={"usuario_id": str(self.inspector.id)},
            content_type="application/json",
        )

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 409)

    def test_corregir_inspeccion_pendiente(self):
        creada = self._crear_inspeccion(avance="50").json()
        url_corregir = reverse(
            "corregir_inspeccion", kwargs={"inspeccion_id": creada["id"]}
        )

        response = self.client.patch(
            url_corregir,
            data={"porcentaje_avance_reportado": "60"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["porcentaje_avance_reportado"], "60.00")

    def test_corregir_inspeccion_confirmada_devuelve_409(self):
        creada = self._crear_inspeccion().json()
        url_confirmar = reverse(
            "confirmar_inspeccion", kwargs={"inspeccion_id": creada["id"]}
        )
        self.client.post(
            url_confirmar,
            data={"usuario_id": str(self.inspector.id)},
            content_type="application/json",
        )

        url_corregir = reverse(
            "corregir_inspeccion", kwargs={"inspeccion_id": creada["id"]}
        )
        response = self.client.patch(
            url_corregir,
            data={"porcentaje_avance_reportado": "90"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)

    def test_bitacora_proyecto_lista_registros_mas_reciente_primero(self):
        creada = self._crear_inspeccion().json()
        url_confirmar = reverse(
            "confirmar_inspeccion", kwargs={"inspeccion_id": creada["id"]}
        )
        self.client.post(
            url_confirmar,
            data={"usuario_id": str(self.inspector.id)},
            content_type="application/json",
        )

        url_bitacora = reverse(
            "bitacora_proyecto", kwargs={"proyecto_id": self.proyecto.id}
        )
        response = self.client.get(url_bitacora)

        self.assertEqual(response.status_code, 200)
        registros = response.json()
        self.assertEqual(len(registros), 3)
        # El mas reciente (avance_actualizado) debe ir primero.
        self.assertEqual(registros[0]["accion"], "avance_actualizado")



class AuthFlowTests(TestCase):
    """
    Cubre el flujo de autenticacion del PASO 12: login/logout, el
    endpoint /me/ (unico con seguridad ya activada), y que los
    endpoints de negocio siguen funcionando SIN token (no forzado).
    """

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Archetype Co.", nit="900777666-1", correo="empresa@civix.test"
        )
        Suscripcion.objects.create(
            empresa=self.empresa,
            plan=Suscripcion.TipoPlan.PROFESIONAL,
            fecha_inicio=date.today(),
            fecha_fin=date(2030, 12, 31),
        )
        self.inspector = Usuario(
            empresa=self.empresa,
            nombre="Julián Cortés",
            correo="julian@civix.test",
            rol=Usuario.Rol.COLABORADOR,
        )
        self.inspector.set_password("clave123")
        self.inspector.save()

        self.gerente = Usuario(
            empresa=self.empresa,
            nombre="Gabriel Márquez",
            correo="gabriel@civix.test",
            rol=Usuario.Rol.GERENTE,
        )
        self.gerente.set_password("otraclave")
        self.gerente.save()

    def test_login_correcto_devuelve_token(self):
        response = self.client.post(
            reverse("auth_login"),
            data={"correo": "julian@civix.test", "contrasena": "clave123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        cuerpo = response.json()
        self.assertIn("token", cuerpo)
        self.assertEqual(cuerpo["usuario"]["es_gerencial"], False)

    def test_login_gerente_marca_es_gerencial(self):
        response = self.client.post(
            reverse("auth_login"),
            data={"correo": "gabriel@civix.test", "contrasena": "otraclave"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["usuario"]["es_gerencial"])

    def test_login_credenciales_invalidas_devuelve_401(self):
        response = self.client.post(
            reverse("auth_login"),
            data={"correo": "julian@civix.test", "contrasena": "incorrecta"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_me_sin_token_devuelve_401(self):
        response = self.client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, 401)

    def test_me_con_token_devuelve_usuario(self):
        token = self.client.post(
            reverse("auth_login"),
            data={"correo": "julian@civix.test", "contrasena": "clave123"},
            content_type="application/json",
        ).json()["token"]

        response = self.client.get(
            reverse("auth_me"), HTTP_AUTHORIZATION=f"Token {token}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["correo"], "julian@civix.test")

    def test_logout_invalida_el_token(self):
        token = self.client.post(
            reverse("auth_login"),
            data={"correo": "julian@civix.test", "contrasena": "clave123"},
            content_type="application/json",
        ).json()["token"]

        logout = self.client.post(
            reverse("auth_logout"),
            data={"token": token},
            content_type="application/json",
        )
        self.assertEqual(logout.status_code, 200)

        me = self.client.get(reverse("auth_me"), HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(me.status_code, 401)

    def test_endpoints_de_negocio_siguen_funcionando_sin_token(self):
        """La seguridad esta PREPARADA pero NO forzada: sin token, los
        endpoints de negocio existentes deben seguir respondiendo 200."""
        url = reverse("crear_proyecto", kwargs={"empresa_id": self.empresa.id})
        response = self.client.get(url)  # listar proyectos, sin token
        self.assertEqual(response.status_code, 200)
