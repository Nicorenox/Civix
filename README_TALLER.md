# Civix - Taller 01 desarrollado

## Qué tenía el proyecto original

La base ya incluía:
- Modelos Empresa, Usuario, Suscripcion y Proyecto.
- Migración inicial.
- Builder para construir Proyecto.
- Service Layer para el caso de uso.
- Factory + Notificador.
- Endpoint POST JSON.
- Configuración básica de Django.

## Qué faltaba

1. Template HTML.
2. Vista Django para renderizar el template.
3. Ruta para abrir el formulario desde el navegador.
4. JavaScript para enviar el formulario al endpoint.
5. Conversión segura de fechas `YYYY-MM-DD` a objetos `date`.
6. Una ruta raíz sencilla para comprobar que el proyecto está funcionando.
7. Pruebas automatizadas del flujo principal.
8. Autenticación/autorización real (pendiente para una versión posterior).

## Ejecutar

```cmd
python manage.py migrate
python manage.py runserver
```

El formulario queda disponible como:

```text
/api/empresas/<UUID_DE_EMPRESA>/proyectos/crear/
```

Primero crea una Empresa y una Suscripcion desde `/admin/`, y luego usa el UUID de esa empresa.

## Nota

El modelo `Usuario` del proyecto es propio y contiene `contrasena_hash`; no reemplaza el sistema de autenticación de Django. Para producción conviene integrar `django.contrib.auth` o un usuario personalizado de Django.
