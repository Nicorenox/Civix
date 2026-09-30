# Civix - Desarrollado Entrega 1

Wiki creada del entregrable 1 con informacion detallada

```bash
  
   
# 1. Clonar el repositorio
git clone https://github.com/Nicorenox/Civix
Cd <Carpeta donde se clono>
cd Civix 

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. (Opcional) Crear superusuario para el panel /admin/
python manage.py createsuperuser

# 6. Correr las pruebas (deben pasar las 11)
python manage.py test

###Puede ocurrir que un test falle ya que se hace aleatoriamente y un test es precisamente que la inspeccion se confirme para que el avance sea actualizado, por ende estso terminos se dan aleatorios y pueden fallar dando:

'inspeccion_confirmada' != 'avance_actualizado' 
FAILED (failures=1)

# 7. Levantar el servidor para pruebas graficas
python manage.py runserver

# 8. Probar
# - Admin:         
http://127.0.0.1:8000/admin/      (Se recomienda hacer esto primero para verificar que existen empresas)

# - Desde admin:    
Crear Empresa -> Crear Suscripción para esa empresa -> crear usuarios

# - Interfaz HTML:  
http://127.0.0.1:8000/api/empresas/<empresa_id>/proyectos/crear/ (<empresa_id> requiere de una empresa creada desde admin, se podra ver ingresando a la empresa de admin, en la barra de buscador aparecera algo parecido a: http://127.0.0.1:8000/admin/proyectos/empresa/f090cff2-cd95-43f7-b20d-3e3b9b17db14/change/. Lo que nos importa para llegar a la interfaz es f090cff2-cd95-43f7-b20d-3e3b9b17db14 , este sera nuestro id de empresa )

# - Login:          
http://127.0.0.1:8000/api/login/ (Desde aca si se creo anteriormente un usuario como colaborador o administrador se dara un panel diferente en el cual se busca dar diferentes roles donde se podra crear una nueva inspeccion y confrimarla apareciendo en la bitacora)

# - API:            
http://127.0.0.1:8000/api/ (Verficar que la API este funcionando)
```
# Civix - Desarrollado Taller 2
- Monolito: Django + Django REST Framework (proyectos, inspecciones, bitácora, autenticación).
- Microservicio (Taller 02, Strangler Pattern): Flask, encargado de la entrega de notificaciones.
- Infraestructura: Docker Compose, Nginx como proxy inverso y PostgreSQL.

 
Nginx decide por la URL: todo lo que empiece por `/api/v2/notificaciones/` va a Flask; el resto va a Django.
Además, Django llama a Flask internamente (red de Docker) cada vez que crea un proyecto o confirma una inspección.

## Estructura

```
civix/
├── docker-compose.yml          # db + django_web + flask_notificaciones + nginx
├── Dockerfile                  # imagen de Django
├── requirements.txt            # dependencias de Django
├── nginx/nginx.conf            # enrutamiento del tráfico
├── flask_notificaciones/       # microservicio
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── test_app.py
├── civix_project/              # configuración Django
└── proyectos/                  # app Django (models, services, infra, views)
```

## Requisitos

- Docker Desktop (en Windows con WSL2 activado)
- Git

Para ejecutar sin Docker (opcional): Python 3.12.

## Ejecutar con Docker (recomendado)

Desde la carpeta `civix/` (donde está `docker-compose.yml`):

```cmd
docker compose up --build
```

La primera vez tarda unos minutos. Django aplica las migraciones automáticamente.
Cuando veas `Container civix-db-1 Healthy` y los logs de gunicorn y Django, todo está arriba.

> Nginx se publica en el puerto **8080** de tu PC. Si ese puerto también está ocupado,
> cambia `"8080:80"` en el servicio `nginx` de `docker-compose.yml`.

Crear el superusuario del admin (en otra terminal):

```cmd
docker compose exec django_web python manage.py createsuperuser
```

Luego entra a `http://localhost:8080/admin/` (usa `http://`, no `https://`) y crea una **Empresa** y su **Suscripción**.
Con el UUID de la empresa abre el formulario:

```
http://localhost:8080/api/empresas/<UUID_DE_EMPRESA>/proyectos/crear/
```

Otras pantallas: `http://localhost:8080/api/login/` y `http://localhost:8080/api/panel/`.

## Probar el microservicio

Todas las pruebas pasan por Nginx (puerto 8080).

| URL | Método | Atiende | Resultado esperado |
|---|---|---|---|
| `/api/` | GET | Django | JSON de bienvenida o listado de la API |
| `/api/v2/notificaciones/health` | GET | Flask | `{"servicio":"notificaciones","estado":"ok"}` |
| `/api/v2/notificaciones/` | POST | Flask | `201` con la notificación creada |
| `/api/v2/notificaciones/` | GET | Flask | Lista de las últimas notificaciones |
| `/api/v2/notificaciones/<id>` | GET | Flask | Detalle o `404` estructurado |

**CMD:**

```cmd
curl -X POST http://localhost:8080/api/v2/notificaciones/ -H "Content-Type: application/json" -d "{\"destinatario\":\"a@b.co\",\"mensaje\":\"hola\",\"proyecto\":{\"nombre\":\"Demo\"}}"
```

**PowerShell:**

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8080/api/v2/notificaciones/ -ContentType "application/json" -Body '{"destinatario":"a@b.co","mensaje":"hola","proyecto":{"nombre":"Demo"}}'
```

Errores estructurados (`400`, `404`, `415`, `500`) tienen siempre esta forma:

```json
{"error": {"codigo": "VALIDACION_FALLIDA", "mensaje": "...", "detalles": {"destinatario": "..."}}}
```

## Comprobar que Django usa el microservicio

1. Crea un proyecto desde el formulario (o confirma una inspección).
2. Mira los logs de Flask:

   ```cmd
   docker compose logs flask_notificaciones
   ```

   Debe aparecer una línea `[DEV-MOCK] a <correo> | Civix - <proyecto> | ...` con el prefijo `flask_notificaciones-1`.
3. Confirma en el historial: `http://localhost:8080/api/v2/notificaciones/` debe listar esa notificación.

> Si el `[DEV-MOCK]` aparece con el prefijo `django_web-1`, significa que Django no pudo llegar a Flask y usó el respaldo por consola.

## Resiliencia (Flask caído)

```cmd
docker compose stop flask_notificaciones
```

Crea otro proyecto: Django **no falla**; tras 3 s de timeout registra una advertencia y usa el notificador por consola.
Para restaurar: `docker compose start flask_notificaciones`.

## Ejecutar sin Docker (desarrollo local)

**Flask** (terminal 1):

```cmd
cd flask_notificaciones
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Django** (terminal 2, usa SQLite al no definir `POSTGRES_DB`):

```cmd
pip install -r requirements.txt
python manage.py migrate
set ENV_TYPE=MICROSERVICIO
set NOTIFICACIONES_URL=http://localhost:5000/api/v2/notificaciones/
python manage.py runserver
```

Sin `ENV_TYPE=MICROSERVICIO`, Django usa el notificador por consola como antes.

## Pruebas automáticas

```cmd
python manage.py test                                # Django (desde civix/)
cd flask_notificaciones && python -m unittest -v test_app   # Flask
```

## Variables de entorno

| Variable | Servicio | Descripción |
|---|---|---|
| `ENV_TYPE` | Django | `DEV` (consola), `REAL` (email), `MICROSERVICIO` (llama a Flask) |
| `NOTIFICACIONES_URL` | Django | URL del microservicio (por defecto `http://flask_notificaciones:5000/api/v2/notificaciones/`) |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` | Django | Si `POSTGRES_DB` existe usa PostgreSQL; si no, SQLite |
| `ENV_TYPE` | Flask | `DEV` (simulado) o `REAL` (etiqueta de envío real) |

## Comandos útiles

```cmd
docker compose ps                   # estado de los contenedores
docker compose logs -f django_web   # logs en vivo de un servicio
docker compose restart nginx        # tras editar nginx.conf
docker compose down                 # detener y eliminar contenedores (conserva la BD)
docker compose down -v              # ATENCIÓN: también borra la base de datos
```
