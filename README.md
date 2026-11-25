# Mesa

Aplicación Django para registrar y dar seguimiento a solicitudes de soporte. Incluye registro e inicio de sesión, solicitudes protegidas por usuario, validación en capas, filtros, trazabilidad, permisos y administración de Django.

## Requisitos

- Python 3.11 o posterior
- Django 5.2

## Inicio local en Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DJANGO_DEBUG = "1"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. La aplicación ofrece registro público; el usuario administrador se crea con `createsuperuser` y el panel interno está en `/admin/`.

## Roles y autorización

Los usuarios autenticados solo pueden ver sus propias solicitudes. Para habilitar la vista global, crea el grupo **Operadores** en Django Admin y asígnale los permisos del modelo Solicitud **Puede ver todas las solicitudes** y **Puede gestionar solicitudes**. La edición del estado usa el permiso `manage_solicitudes`; la vista global usa `view_all_solicitudes`. El acceso a `/admin/` se reserva a cuentas con `is_staff`.

## Seguridad y configuración de despliegue

`DJANGO_DEBUG` es falso por defecto. En producción, configura `DJANGO_SECRET_KEY` con un secreto aleatorio, `DJANGO_ALLOWED_HOSTS` con los dominios reales, HTTPS detrás de un proxy confiable y mantén `DJANGO_DEBUG` desactivado. Las cookies `Secure`, HSTS y la redirección HTTPS se activan al desactivar el modo debug. No uses la clave de desarrollo incluida como valor de producción.

El middleware limpia solamente campos de texto permitidos, registra método/ruta/estado/actor y agrega una política CSP, `X-Content-Type-Options` y `Referrer-Policy`. Las páginas usan autoescape de Django. Los formularios POST incluyen token CSRF y la salida nunca se guarda desde `request.POST` sin validar un formulario.

Verificaciones:

```powershell
python manage.py check
python manage.py check --deploy
python manage.py test
```
