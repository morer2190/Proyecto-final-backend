# Proyecto Final Backend

API RESTful desarrollada con Flask y SQLAlchemy para la gestión de usuarios, proveedores, cotizaciones y reservaciones.

## Requisitos

- Python 3.8 o superior
- MySQL Server

## Instalación

1. Clonar el repositorio o descargar los archivos del proyecto.

2. Instalar las dependencias ejecutando en la terminal:
   ```
   pip install -r dependencias.txt
   ```

3. Crear el archivo `.env` en la raíz del proyecto con el siguiente contenido (ajustar valores según la configuración de MySQL):

   ```
   DB_USER=usuario_mysql
   DB_PASSWORD=contraseña_mysql
   JWT_SECRET_KEY=clave_secreta_jwt
   ```

4. La base de datos debe existir en MySQL con el nombre `default` o modificar el nombre en la cadena de conexión en `app.py`:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://usuario:contraseña@localhost/default?auth_plugin=caching_sha2_password'
   ```

5. Las tablas se inicializan automáticamente al ejecutar la aplicación si no existen.

## Ejecución

Ejecutar en la terminal:
```
python app.py
```
La API queda disponible en [http://localhost:5000](http://localhost:5000).

## Cambios recientes y validaciones

- Validaciones estrictas para campos obligatorios, unicidad de cédula, formato de correo electrónico y URL, y verificación de valores válidos en enums (`rol`, `tipo`, `estado`).
- Los campos `cedula`, `contrasena` y `rol` no son actualizables mediante el endpoint PUT de usuarios.
- Autenticación JWT requerida en endpoints protegidos, usando el header `Authorization`.
- Filtrado por usuario en cotizaciones y reservaciones: administradores y agentes visualizan todos los registros, clientes solo los propios.
- Asignación de valores por defecto en campos `estado` de cotizaciones y reservaciones.
- Validación de fechas en reservaciones, asegurando formato correcto y que la fecha de fin sea posterior a la de inicio.

## Endpoints principales

- `/usuarios` (GET, POST, PUT)
- `/proveedores` (GET, POST, PUT, DELETE)
- `/cotizaciones` (GET, POST, PUT, DELETE)
- `/reservaciones` (GET, POST, PUT, DELETE)
- `/login` (POST) — autenticación y obtención de token JWT

---