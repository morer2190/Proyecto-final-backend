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
    fecha_creacion = Column(Date, nullable=False, default=db.func.current_date())
    fecha_actualizacion = Column(Date, nullable=False, default=db.func.current_date())

     # Método para setear la contraseña
    def set_password(self, password: str):
        salt = bcrypt.gensalt()
        self.hash_contrasena = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    
    # Método para verificar la contraseña
    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.hash_contrasena.encode("utf-8"))

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "cedula": self.cedula, "correo_electronico": self.correo_electronico, "rol": self.get_rol_name(), "fecha_creacion": self.fecha_creacion, "fecha_actualizacion": self.fecha_actualizacion}
    
    def get_rol_name(self):
        return self.rol.name if self.rol else None

class Proveedor(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200))
    tipo = Column(SqlEnum(TipoProveedor))
    enlace = Column(String(500))
    fecha_creacion = Column(Date, nullable=False, default=db.func.current_date())
    fecha_actualizacion = Column(Date, nullable=False, default=db.func.current_date())

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "tipo":  TipoProveedor(self.tipo).name, "enlace": self.enlace, "fecha_creacion": self.fecha_creacion, "fecha_actualizacion": self.fecha_actualizacion}

class Cotizacion(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    servicio = Column(String(100), nullable=False)
    detalle = Column(String(500), nullable=False)
    estado = Column(SqlEnum(EstadoCotizacion), nullable=False)
    fecha_creacion = Column(Date, nullable=False, default=db.func.current_date())
    fecha_actualizacion = Column(Date, nullable=False, default=db.func.current_date())

    def to_dict(self):
        return {"id": self.id, "servicio": self.servicio, "detalle": self.detalle, "estado": EstadoCotizacion(self.estado).name, "fecha_creacion": self.fecha_creacion, "fecha_actualizacion": self.fecha_actualizacion}

class Reservacion(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    detalle = Column(String(500), nullable=False)
    estado = Column(SqlEnum(EstadoReservacion), nullable=False, default=EstadoReservacion.Confirmada)
    id_usuario = Column(Integer, db.ForeignKey('usuario.id'), nullable=False)
    # Opcional: relación para acceder al usuario desde la reservación
    usuario = db.relationship('Usuario', backref='reservaciones')
    fecha_creacion = Column(Date, nullable=False, default=db.func.current_date())
    fecha_actualizacion = Column(Date, nullable=False, default=db.func.current_date())

    def to_dict(self):
        return {
            "id": self.id,
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "detalle": self.detalle,
            "estado": EstadoReservacion(self.estado).name,
            "id_usuario": self.id_usuario,
            "fecha_creacion": self.fecha_creacion,
            "fecha_actualizacion": self.fecha_actualizacion
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

    # Validación de correo electrónico con regex
    import re
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, data['correo_electronico']):
        return jsonify({"error": "El correo electrónico no es válido"}), 400

    # Validación de unicidad de cedula
    if Usuario.query.filter_by(cedula=data['cedula']).first():
        return jsonify({"error": "La cédula ya está registrada"}), 400

    # Validación de rol
    rol_value = data['rol']
    valid_roles = [r.name for r in Rol]
    if isinstance(rol_value, int):
        try:
            rol_enum = Rol(rol_value)
        except ValueError:
            return jsonify({"error": f"El rol '{rol_value}' no es válido"}), 400
    else:
        if rol_value not in valid_roles:
            return jsonify({"error": f"El rol '{rol_value}' no es válido"}), 400
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
    if not data.get('enlace'):
        return jsonify({"error": "El campo 'enlace' es obligatorio"}), 400

    # Validación de enlace como URL con regex
    import re
    url_regex = r"^(https?://)?([\w\-]+\.)+[\w\-]+(/[^\sß]*)?$"
    if not re.match(url_regex, data['enlace']):
        return jsonify({"error": "El campo 'enlace' debe ser una URL válida"}), 400

    # Validación de tipo proveedor
    tipo_value = data.get('tipo')
    valid_tipos = [t.name for t in TipoProveedor]
    if isinstance(tipo_value, int):
        try:
            tipo_enum = TipoProveedor(tipo_value)
        except ValueError:
            return jsonify({"error": f"El tipo '{tipo_value}' no es válido"}), 400
    else:
        if tipo_value not in valid_tipos:
            return jsonify({"error": f"El tipo '{tipo_value}' no es válido"}), 400
        tipo_enum = TipoProveedor[tipo_value]

    nuevo = Proveedor(nombre=data['nombre'], tipo=tipo_enum, enlace=data['enlace'])
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({"mensaje": "Proveedor creado", "proveedor": nuevo.to_dict()}), 201

@app.route('/proveedores/<int:id>', methods=['PUT'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
def actualizar_proveedor(id):
    data = request.get_json()
    proveedor = Proveedor.query.get_or_404(id)

    # Validación de nombre
    if 'nombre' in data and not data['nombre']:
        return jsonify({"error": "El campo 'nombre' es obligatorio"}), 400

    # Validación de enlace como URL con regex
    if 'enlace' in data:
        if not data['enlace']:
            return jsonify({"error": "El campo 'enlace' es obligatorio"}), 400
        import re
        url_regex = r"^(https?://)?([\w\-]+\.)+[\w\-]+(/[^\sß]*)?$"
        if not re.match(url_regex, data['enlace']):
            return jsonify({"error": "El campo 'enlace' debe ser una URL válida"}), 400
        proveedor.enlace = data['enlace']

    # Validación de tipo proveedor
    if 'tipo' in data:
        tipo_value = data['tipo']
        valid_tipos = [t.name for t in TipoProveedor]
        if isinstance(tipo_value, int):
            try:
                tipo_enum = TipoProveedor(tipo_value)
            except ValueError:
                return jsonify({"error": f"El tipo '{tipo_value}' no es válido"}), 400
        else:
            if tipo_value not in valid_tipos:
                return jsonify({"error": f"El tipo '{tipo_value}' no es válido"}), 400
            tipo_enum = TipoProveedor[tipo_value]
        proveedor.tipo = tipo_enum

    if 'nombre' in data and data['nombre']:
        proveedor.nombre = data['nombre']

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
@role_required([Rol.Administrador.name, Rol.Cliente.name, Rol.Agente.name])
def crear_cotizacion():
    data = request.get_json()
    # Validaciones de campos obligatorios
    if not data.get('servicio'):
        return jsonify({"error": "El campo 'servicio' es obligatorio"}), 400
    if not data.get('detalle'):
        return jsonify({"error": "El campo 'detalle' es obligatorio"}), 400

    # Estado por defecto: Pendiente

    nueva = Cotizacion(
        servicio=data['servicio'],
        detalle=data['detalle'],
        estado=EstadoCotizacion.Pendiente.name,  # Estado por defecto
    )
    db.session.add(nueva)
    db.session.commit()
    return jsonify({"mensaje": "Cotización creada", "cotizacion": nueva.to_dict()}), 201

@app.route('/cotizaciones/<int:id>', methods=['PUT'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
def actualizar_cotizacion(id):
    data = request.get_json()
    cotizacion = Cotizacion.query.get_or_404(id)

    # Validaciones de campos obligatorios
    if not data.get('servicio'):
        return jsonify({"error": "El campo 'servicio' es obligatorio"}), 400
    if not data.get('detalle'):
        return jsonify({"error": "El campo 'detalle' es obligatorio"}), 400
    if not data.get('estado'):
        return jsonify({"error": "El campo 'estado' es obligatorio"}), 400

    estado_value = data['estado']
    valid_estados = [e.name for e in EstadoCotizacion]
    if isinstance(estado_value, int):
        try:
            estado_enum = EstadoCotizacion(estado_value)
        except ValueError:
            return jsonify({"error": f"El estado '{estado_value}' no es válido"}), 400
    else:
        if estado_value not in valid_estados:
            return jsonify({"error": f"El estado '{estado_value}' no es válido"}), 400
        estado_enum = EstadoCotizacion[estado_value]

    cotizacion.servicio = data['servicio']
    cotizacion.detalle = data['detalle']
    cotizacion.estado = estado_enum

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
    from datetime import datetime

    data = request.get_json()

    # Validaciones de campos obligatorios
    if not data.get('fecha_inicio'):
        return jsonify({"error": "El campo 'fecha_inicio' es obligatorio"}), 400
    if not data.get('fecha_fin'):
        return jsonify({"error": "El campo 'fecha_fin' es obligatorio"}), 400
    if not data.get('detalle'):
        return jsonify({"error": "El campo 'detalle' es obligatorio"}), 400
    if not data.get('id_usuario'):
        return jsonify({"error": "El campo 'id_usuario' es obligatorio"}), 400

    # Validación de fechas
    try:
        fecha_inicio = datetime.strptime(data['fecha_inicio'], "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "El campo 'fecha_inicio' debe tener formato YYYY-MM-DD"}), 400

    try:
        fecha_fin = datetime.strptime(data['fecha_fin'], "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "El campo 'fecha_fin' debe tener formato YYYY-MM-DD"}), 400

    if fecha_fin <= fecha_inicio:
        return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400

    nueva = Reservacion(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        detalle=data['detalle'],
        estado=EstadoReservacion.Confirmada.name,  # Estado por defecto
        id_usuario=data['id_usuario']
    )
    db.session.add(nueva)
    db.session.commit()
    return jsonify({"mensaje": "Reservación creada", "reservacion": nueva.to_dict()}), 201

@app.route('/reservaciones/<int:id>', methods=['PUT'])
@role_required([Rol.Administrador.name, Rol.Agente.name])
def actualizar_reservacion(id):
    from datetime import datetime

    data = request.get_json()
    reservacion = Reservacion.query.get_or_404(id)

    # Validaciones de campos obligatorios
    if not data.get('fecha_inicio'):
        return jsonify({"error": "El campo 'fecha_inicio' es obligatorio"}), 400
    if not data.get('fecha_fin'):
        return jsonify({"error": "El campo 'fecha_fin' es obligatorio"}), 400
    if not data.get('detalle'):
        return jsonify({"error": "El campo 'detalle' es obligatorio"}), 400
    if not data.get('id_usuario'):
        return jsonify({"error": "El campo 'id_usuario' es obligatorio"}), 400
    if not data.get('estado'):
        return jsonify({"error": "El campo 'estado' es obligatorio"}), 400

    # Validación de fechas
    try:
        fecha_inicio = datetime.strptime(data['fecha_inicio'], "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "El campo 'fecha_inicio' debe tener formato YYYY-MM-DD"}), 400

    try:
        fecha_fin = datetime.strptime(data['fecha_fin'], "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "El campo 'fecha_fin' debe tener formato YYYY-MM-DD"}), 400

    if fecha_fin <= fecha_inicio:
        return jsonify({"error": "La fecha de fin debe ser posterior a la fecha de inicio"}), 400

    # Validación de estado
    estado_value = data['estado']
    valid_estados = [e.name for e in EstadoReservacion]
    if isinstance(estado_value, int):
        try:
            estado_enum = EstadoReservacion(estado_value)
        except ValueError:
            return jsonify({"error": f"El estado '{estado_value}' no es válido"}), 400
    else:
        if estado_value not in valid_estados:
            return jsonify({"error": f"El estado '{estado_value}' no es válido"}), 400
        estado_enum = EstadoReservacion[estado_value]

    reservacion.fecha_inicio = fecha_inicio
    reservacion.fecha_fin = fecha_fin
    reservacion.detalle = data['detalle']
    reservacion.estado = estado_enum
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

