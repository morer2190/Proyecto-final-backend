import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Enum as SqlEnum, Date
from dotenv import load_dotenv
from enum import Enum
load_dotenv()

app = Flask(__name__)

db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASSWORD', '')

# Configura la conexión a MySQL (ajusta usuario, contraseña, host y base de datos)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@localhost/default?auth_plugin=caching_sha2_password'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Rol(Enum):
    Cliente = 1
    Agente = 2

class EstadoCotizacion(Enum):
    Pendiente = 1
    Respondida = 2
    Aceptada = 3
    Rechazada = 4

class EstadoReservacion(Enum):
    Completada = 1
    Cancelada = 2
    Confirmada = 3

class TipoProveedor(Enum):
    Hotel = 1
    Tour = 2
    Agencia = 3
    RentaVehiculo = 4

class Usuario(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200))
    cedula = Column(String(50), unique=True)
    correo_electronico = Column(String(100))
    contrasena = Column(String(100))
    rol = Column(SqlEnum(Rol), default=Rol.Cliente)

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "cedula": self.cedula, "correo_electronico": self.correo_electronico, "rol": Rol(self.rol).name }

class Proveedor(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200))
    tipo = Column(SqlEnum(TipoProveedor))
    enlace = Column(String(500))

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "tipo":  TipoProveedor(self.tipo).name, "enlace": self.enlace }

class Cotizacion(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    servicio = Column(String(100), nullable=False)
    detalle = Column(String(500), nullable=False)
    estado = Column(SqlEnum(EstadoCotizacion), nullable=False)

    def to_dict(self):
        return {"id": self.id, "servicio": self.servicio, "detalle": self.detalle, "estado": EstadoCotizacion(self.estado).name }

class Reservacion(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    detalle = Column(String(500), nullable=False)
    estado = Column(SqlEnum(EstadoReservacion), nullable=False, default=EstadoReservacion.Confirmada)
    id_usuario = Column(Integer, db.ForeignKey('usuario.id'), nullable=False)
    # Opcional: relación para acceder al usuario desde la reservación
    usuario = db.relationship('Usuario', backref='reservaciones')

    def to_dict(self):
        return {
            "id": self.id,
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "detalle": self.detalle,
            "estado": EstadoReservacion(self.estado).name,
            "id_usuario": self.id_usuario
        }

# Ruta GET para la raíz ("/")
@app.route('/')
def inicio():
    return ""

# Ruta GET para obtener todos los usuarios
@app.route('/usuarios', methods=['GET'])
def obtener_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([u.to_dict() for u in usuarios])

# Ruta POST para crear un nuevo usuario
@app.route('/usuarios', methods=['POST'])
def crear_usuario():
    data = request.get_json()
    # Validaciones
    if not data.get('nombre'):
        return jsonify({"error": "El campo 'nombre' es obligatorio"}), 400
    if not data.get('cedula'):
        return jsonify({"error": "El campo 'cedula' es obligatorio"}), 400
    rol_value = data['rol']
    if isinstance(rol_value, int):
        rol_enum = Rol(rol_value)
    else:
        rol_enum = Rol[rol_value]
    nuevo_usuario = Usuario(
        nombre=data['nombre'],
        cedula=data['cedula'],
        correo_electronico=data['correo_electronico'],
        contrasena=data['contrasena'],
        rol=rol_enum
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify({"mensaje": "Usuario creado", "usuario": nuevo_usuario.to_dict()}), 201

# --- CRUD Proveedor ---
@app.route('/proveedores', methods=['GET'])
def obtener_proveedores():
    proveedores = Proveedor.query.all()
    return jsonify([p.to_dict() for p in proveedores])

@app.route('/proveedores', methods=['POST'])
def crear_proveedor():
    data = request.get_json()
    # Validación
    if not data.get('nombre'):
        return jsonify({"error": "El campo 'nombre' es obligatorio"}), 400
    tipo = data['tipo']
    tipo_enum = TipoProveedor(tipo) if isinstance(tipo, int) else TipoProveedor[tipo]
    nuevo = Proveedor(nombre=data['nombre'], tipo=tipo_enum, enlace=data['enlace'])
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"mensaje": "Proveedor creado", "proveedor": nuevo.to_dict()}), 201

@app.route('/proveedores/<int:id>', methods=['PUT'])
def actualizar_proveedor(id):
    data = request.get_json()
    proveedor = Proveedor.query.get_or_404(id)
    proveedor.nombre = data.get('nombre', proveedor.nombre)
    if 'tipo' in data:
        tipo = data['tipo']
        proveedor.tipo = TipoProveedor(tipo) if isinstance(tipo, int) else TipoProveedor[tipo]
    proveedor.enlace = data.get('enlace', proveedor.enlace)
    db.session.commit()
    return jsonify(proveedor.to_dict())

@app.route('/proveedores/<int:id>', methods=['DELETE'])
def eliminar_proveedor(id):
    proveedor = Proveedor.query.get_or_404(id)
    db.session.delete(proveedor)
    db.session.commit()
    return jsonify({"mensaje": "Proveedor eliminado"})

# --- CRUD Cotizacion ---
@app.route('/cotizaciones', methods=['GET'])
def obtener_cotizaciones():
    cotizaciones = Cotizacion.query.all()
    return jsonify([c.to_dict() for c in cotizaciones])

@app.route('/cotizaciones', methods=['POST'])
def crear_cotizacion():
    data = request.get_json()
    estado = data['estado']
    estado_enum = EstadoCotizacion(estado) if isinstance(estado, int) else EstadoCotizacion[estado]
    nueva = Cotizacion(servicio=data['servicio'], detalle=data['detalle'], estado=estado_enum)
    db.session.add(nueva)
    db.session.commit()
    return jsonify({"mensaje": "Cotización creada", "cotizacion": nueva.to_dict()}), 201

@app.route('/cotizaciones/<int:id>', methods=['PUT'])
def actualizar_cotizacion(id):
    data = request.get_json()
    cotizacion = Cotizacion.query.get_or_404(id)
    cotizacion.servicio = data.get('servicio', cotizacion.servicio)
    cotizacion.detalle = data.get('detalle', cotizacion.detalle)
    if 'estado' in data:
        estado = data['estado']
        cotizacion.estado = EstadoCotizacion(estado) if isinstance(estado, int) else EstadoCotizacion[estado]
    db.session.commit()
    return jsonify(cotizacion.to_dict())

@app.route('/cotizaciones/<int:id>', methods=['DELETE'])
def eliminar_cotizacion(id):
    cotizacion = Cotizacion.query.get_or_404(id)
    db.session.delete(cotizacion)
    db.session.commit()
    return jsonify({"mensaje": "Cotización eliminada"})

# --- CRUD Reservacion ---
@app.route('/reservaciones', methods=['GET'])
def obtener_reservaciones():
    reservaciones = Reservacion.query.all()
    return jsonify([r.to_dict() for r in reservaciones])

@app.route('/reservaciones', methods=['POST'])
def crear_reservacion():
    data = request.get_json()
    estado = data.get('estado', EstadoReservacion.Confirmada.name)
    estado_enum = EstadoReservacion(estado) if isinstance(estado, int) else EstadoReservacion[estado]
    nueva = Reservacion(
        fecha_inicio=data['fecha_inicio'],
        fecha_fin=data['fecha_fin'],
        detalle=data['detalle'],
        estado=estado_enum,
        id_usuario=data['id_usuario']
    )
    db.session.add(nueva)
    db.session.commit()
    return jsonify({"mensaje": "Reservación creada", "reservacion": nueva.to_dict()}), 201

@app.route('/reservaciones/<int:id>', methods=['PUT'])
def actualizar_reservacion(id):
    data = request.get_json()
    reservacion = Reservacion.query.get_or_404(id)
    reservacion.fecha_inicio = data.get('fecha_inicio', reservacion.fecha_inicio)
    reservacion.fecha_fin = data.get('fecha_fin', reservacion.fecha_fin)
    reservacion.detalle = data.get('detalle', reservacion.detalle)
    if 'estado' in data:
        estado = data['estado']
        reservacion.estado = EstadoReservacion(estado) if isinstance(estado, int) else EstadoReservacion[estado]
    if 'id_usuario' in data:
        reservacion.id_usuario = data['id_usuario']
    db.session.commit()
    return jsonify(reservacion.to_dict())

@app.route('/reservaciones/<int:id>', methods=['DELETE'])
def eliminar_reservacion(id):
    reservacion = Reservacion.query.get_or_404(id)
    db.session.delete(reservacion)
    db.session.commit()
    return jsonify({"mensaje": "Reservación eliminada"})

if __name__ == '__main__':
    # Crea las tablas si no existen
    with app.app_context():
        db.create_all()
    app.run(port=5000, debug=True)           # Iniciar servidor en puerto 5000

