import os
import bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Enum as SqlEnum, Date
from dotenv import load_dotenv
from enum import Enum
from decorator.role_required import role_required
load_dotenv()

app = Flask(__name__)

db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASSWORD', '')

# Configura la conexión a MySQL (ajusta usuario, contraseña, host y base de datos)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@localhost/default?auth_plugin=caching_sha2_password'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

db = SQLAlchemy(app)

class Rol(Enum):
    Cliente = 1
    Agente = 2
    Administrador = 3

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
    hash_contrasena = Column(String(100))
    rol = Column(SqlEnum(Rol), default=Rol.Cliente)

     # Método para setear la contraseña
    def set_password(self, password: str):
        salt = bcrypt.gensalt()
        self.hash_contrasena = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    
    # Método para verificar la contraseña
    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.hash_contrasena.encode("utf-8"))

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "cedula": self.cedula, "correo_electronico": self.correo_electronico, "rol": self.get_rol_name() }
    
    def get_rol_name(self):
        return self.rol.name if self.rol else None

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

# Login que genera un token
@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data.get('correo_electronico'):
        return jsonify({"error": "El campo 'correo_electronico' es obligatorio"}), 400

    if not data.get('contrasena'):
        return jsonify({"error": "El campo 'contrasena' es obligatorio"}), 400

    correo_electronico = data.get("correo_electronico", None)
    contrasena = data.get("contrasena", None)

    usuarios = Usuario.query.filter_by(correo_electronico=correo_electronico).all()

    if not usuarios or not usuarios[0].check_password(contrasena):
        return jsonify({"msg": "Credenciales inválidas"}), 401

    token = create_access_token(identity=correo_electronico, additional_claims={'role': usuarios[0].get_rol_name()})
    return jsonify(access_token=token)


# Ruta GET para obtener todos los usuarios
@app.route('/usuarios', methods=['GET'])
@role_required([Rol.Administrador.name])  # Solo permite acceso a usuarios con rol Administrador
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
    if not data.get('contrasena'):
        return jsonify({"error": "El campo 'contrasena' es obligatorio"}), 400
    if not data.get('correo_electronico'):
        return jsonify({"error": "El campo 'correo_electronico' es obligatorio"}), 400
    rol_value = data['rol']
    if isinstance(rol_value, int):
        rol_enum = Rol(rol_value)
    else:
        rol_enum = Rol[rol_value]
  
    nuevo_usuario = Usuario(
        nombre=data['nombre'],
        cedula=data['cedula'],
        correo_electronico=data['correo_electronico'],
        rol=rol_enum
    )
    nuevo_usuario.set_password(data.get('contrasena'))


    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify({"mensaje": "Usuario creado", "usuario": nuevo_usuario.to_dict()}), 201

# --- CRUD Proveedor ---
@app.route('/proveedores', methods=['GET'])
@role_required([Rol.Administrador.name])  # Solo permite acceso a usuarios con rol Administrador
def obtener_proveedores():
    proveedores = Proveedor.query.all()
    return jsonify([p.to_dict() for p in proveedores])

@app.route('/proveedores', methods=['POST'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
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
@role_required([Rol.Administrador.name, Rol.Agente.name])
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
@role_required([Rol.Administrador.name])
def eliminar_proveedor(id):
    proveedor = Proveedor.query.get_or_404(id)
    db.session.delete(proveedor)
    db.session.commit()
    return jsonify({"mensaje": "Proveedor eliminado"})

# --- CRUD Cotizacion ---
@app.route('/cotizaciones', methods=['GET'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
def obtener_cotizaciones():
    cotizaciones = Cotizacion.query.all()
    return jsonify([c.to_dict() for c in cotizaciones])

@app.route('/cotizaciones', methods=['POST'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
def crear_cotizacion():
    data = request.get_json()
    estado = data['estado']
    estado_enum = EstadoCotizacion(estado) if isinstance(estado, int) else EstadoCotizacion[estado]
    nueva = Cotizacion(servicio=data['servicio'], detalle=data['detalle'], estado=estado_enum)
    db.session.add(nueva)
    db.session.commit()
    return jsonify({"mensaje": "Cotización creada", "cotizacion": nueva.to_dict()}), 201

@app.route('/cotizaciones/<int:id>', methods=['PUT'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
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
@role_required([Rol.Administrador.name, Rol.Agente.name])
def eliminar_cotizacion(id):
    cotizacion = Cotizacion.query.get_or_404(id)
    db.session.delete(cotizacion)
    db.session.commit()
    return jsonify({"mensaje": "Cotización eliminada"})

# --- CRUD Reservacion ---
@app.route('/reservaciones', methods=['GET'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
def obtener_reservaciones():
    reservaciones = Reservacion.query.all()
    return jsonify([r.to_dict() for r in reservaciones])

@app.route('/reservaciones', methods=['POST'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
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
@role_required([Rol.Administrador.name, Rol.Agente.name])
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
@role_required([Rol.Administrador.name, Rol.Agente.name])
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

