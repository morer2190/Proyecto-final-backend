# Proyecto Final Backend

Este proyecto es una API RESTful construida con Flask y SQLAlchemy para la gestión de usuarios, proveedores, cotizaciones y reservaciones.

## Requisitos

- Python 3.8 o superior
- MySQL Server

## Instalación

1. **Clona el repositorio o descarga los archivos del proyecto.**

2. **Instala las dependencias:**

   Abre una terminal en la carpeta del proyecto y ejecuta:
   ```
   pip install -r dependencias.txt
   ```

3. **Configura las variables de entorno:**

   Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido (ajusta los valores según tu configuración de MySQL):

   ```
   DB_USER=tu_usuario_mysql
   DB_PASSWORD=tu_contraseña_mysql
   ```

4. **Configura la base de datos:**

   Asegúrate de tener una base de datos creada en MySQL llamada `default` o cambia el nombre en la cadena de conexión dentro de `App.py`:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://usuario:contraseña@localhost/default?auth_plugin=caching_sha2_password'
   ```

5. **Inicializa las tablas:**

   Al ejecutar la aplicación por primera vez, las tablas se crearán automáticamente si no existen.

## Ejecución

En la terminal, ejecuta:

```
python App.py
```

La API estará disponible en [http://localhost:5000](http://localhost:5000).

## Endpoints principales

- `/usuarios` (GET, POST)
- `/proveedores` (GET, POST, PUT, DELETE)
- `/cotizaciones` (GET, POST, PUT, DELETE)
- `/reservaciones` (GET, POST, PUT, DELETE)

---