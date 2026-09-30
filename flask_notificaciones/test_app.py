import unittest
from unittest.mock import patch

from app import create_app

URL = "/api/v2/notificaciones/"
VALIDO = {
    "destinatario": "demo@civix.test",
    "mensaje": "El proyecto 'Torre Norte' fue creado exitosamente.",
    "proyecto": {"id": "abc", "nombre": "Torre Norte"},
}


class NotificacionesTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_health(self):
        r = self.client.get(URL + "health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["estado"], "ok")

    def test_crear_ok_201(self):
        r = self.client.post(URL, json=VALIDO)
        self.assertEqual(r.status_code, 201)
        body = r.get_json()
        self.assertEqual(body["estado"], "enviada")
        self.assertEqual(body["canal"], "email")
        self.assertEqual(body["asunto"], "Civix - Torre Norte")

    def test_listar_y_detalle(self):
        creada = self.client.post(URL, json=VALIDO).get_json()
        self.assertEqual(len(self.client.get(URL).get_json()), 1)
        r = self.client.get(URL + creada["id"])
        self.assertEqual(r.status_code, 200)

    def test_detalle_inexistente_404(self):
        r = self.client.get(URL + "no-existe")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"]["codigo"], "NO_ENCONTRADA")

    def test_validacion_400(self):
        r = self.client.post(URL, json={"destinatario": "mal", "canal": "fax"})
        self.assertEqual(r.status_code, 400)
        err = r.get_json()["error"]
        self.assertEqual(err["codigo"], "VALIDACION_FALLIDA")
        for campo in ("destinatario", "mensaje", "proyecto.nombre", "canal"):
            self.assertIn(campo, err["detalles"])

    def test_json_malformado_400(self):
        r = self.client.post(URL, data="{no es json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["codigo"], "JSON_MALFORMADO")

    def test_json_no_objeto_400(self):
        r = self.client.post(URL, json=[1, 2, 3])
        self.assertEqual(r.status_code, 400)

    def test_content_type_415(self):
        r = self.client.post(URL, data="hola", content_type="text/plain")
        self.assertEqual(r.status_code, 415)

    def test_metodo_no_permitido_405_estructurado(self):
        r = self.client.delete(URL)
        self.assertEqual(r.status_code, 405)
        self.assertIn("error", r.get_json())

    def test_error_inesperado_500_estructurado(self):
        app = create_app()
        app.config["PROPAGATE_EXCEPTIONS"] = False
        client = app.test_client()
        with patch("app.entregar", side_effect=RuntimeError("boom")):
            r = client.post(URL, json=VALIDO)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json()["error"]["codigo"], "ERROR_INTERNO")
        self.assertNotIn("boom", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
