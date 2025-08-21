import unittest
from app import app, db, Usuario, Proveedor, Cotizacion, Reservacion, Rol, TipoProveedor, EstadoCotizacion, EstadoReservacion
from flask import json

class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def create_usuario(self, nombre="Test", cedula="123", correo="test@example.com", contrasena="pass", rol=Rol.Cliente.name):
        data = {
            "nombre": nombre,
            "cedula": cedula,
            "correo_electronico": correo,
            "contrasena": contrasena,
            "rol": rol
        }
        return self.client.post("/usuarios", data=json.dumps(data), content_type="application/json")

    def login_and_get_token(self, correo="test@example.com", contrasena="pass"):
        data = {
            "correo_electronico": correo,
            "contrasena": contrasena
        }
        res = self.client.post("/login", data=json.dumps(data), content_type="application/json")
        token = json.loads(res.data).get("access_token")
        return token

    def test_crear_usuario(self):
        res = self.create_usuario()
        self.assertEqual(res.status_code, 201)
        self.assertIn("Usuario creado", res.get_data(as_text=True))

    def test_crear_usuario_email_invalido(self):
        res = self.create_usuario(correo="bademail")
        self.assertEqual(res.status_code, 400)

    def test_crear_usuario_cedula_duplicada(self):
        self.create_usuario()
        res = self.create_usuario(cedula="123", correo="other@example.com")
        self.assertEqual(res.status_code, 400)

    def test_crear_usuario_rol_invalido(self):
        res = self.create_usuario(rol="NoExiste")
        self.assertEqual(res.status_code, 400)

    def test_crear_proveedor(self):
        # Crear usuario administrador y obtener token
        self.create_usuario(correo="admin@example.com", cedula="999", rol=Rol.Administrador.name)
        token = self.login_and_get_token(correo="admin@example.com")
        data = {
            "nombre": "Proveedor1",
            "tipo": TipoProveedor.Hotel.name,
            "enlace": "https://hotel.com"
        }
        res = self.client.post(
            "/proveedores",
            data=json.dumps(data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 201)

    def test_crear_proveedor_enlace_invalido(self):
        self.create_usuario(correo="admin@example.com", cedula="999", rol=Rol.Administrador.name)
        token = self.login_and_get_token(correo="admin@example.com")
        data = {
            "nombre": "Proveedor2",
            "tipo": TipoProveedor.Hotel.name,
            "enlace": "badurl"
        }
        res = self.client.post(
            "/proveedores",
            data=json.dumps(data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 400)

    def test_crear_cotizacion(self):
        # Crear usuario primero
        self.create_usuario()
        with app.app_context():
            usuario_id = Usuario.query.filter_by(cedula="123").first().id
        token = self.login_and_get_token()
        data = {
            "servicio": "Servicio1",
            "detalle": "Detalle1",
            "id_usuario": usuario_id
        }
        res = self.client.post(
            "/cotizaciones",
            data=json.dumps(data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 201)

    def test_crear_reservacion(self):
        self.create_usuario(correo="admin@example.com", cedula="999", rol=Rol.Administrador.name)
        token = self.login_and_get_token(correo="admin@example.com")
        with app.app_context():
            usuario_id = Usuario.query.filter_by(cedula="999").first().id
        data = {
            "fecha_inicio": "2025-08-21",
            "fecha_fin": "2025-08-22",
            "detalle": "Reserva test",
            "id_usuario": usuario_id
        }
        res = self.client.post(
            "/reservaciones",
            data=json.dumps(data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 201)

    def test_crear_reservacion_fecha_invalida(self):
        self.create_usuario(correo="admin@example.com", cedula="999", rol=Rol.Administrador.name)
        token = self.login_and_get_token(correo="admin@example.com")
        with app.app_context():
            usuario_id = Usuario.query.filter_by(cedula="999").first().id
        data = {
            "fecha_inicio": "2025-08-22",
            "fecha_fin": "2025-08-21",
            "detalle": "Reserva test",
            "id_usuario": usuario_id
        }
        res = self.client.post(
            "/reservaciones",
            data=json.dumps(data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 400)

if __name__ == "__main__":
    unittest.main()