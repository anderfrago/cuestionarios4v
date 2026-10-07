# Cuestionarios Cuatrovientos

Aplicación Flask + Angular 21 para gestionar los distintos cuestionarios del centro. Incluye roles de alumnado, tutoría y administración; invitaciones por código; formularios versionados y editables; múltiples intentos; alertas protegidas; análisis individual/grupal y exportación Excel/PDF.

Consulta primero la [guía de privacidad y actualización](docs/PRIVACIDAD_Y_ACTUALIZACION.md), con diagrama, migración y requisitos pendientes. Los formularios sensibles o sin revisar están bloqueados por defecto.

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Completar claves, SMTP y correos autorizados. En HTTP local: COOKIE_SECURE=false.
flask --app backend.app db upgrade
flask --app backend.app seed-data
flask --app backend.app run --debug
```

En otra terminal:

```bash
cd frontend
npm ci
npm start
```

La API queda en `http://127.0.0.1:5000` y Angular en `http://localhost:4200`.

## Decisiones funcionales

- Cada curso puede tener varios formularios publicados asignados.
- Las versiones publicadas son inmutables; cualquier edición crea una versión nueva y preserva los intentos anteriores.
- Tipos disponibles: sí/no, desplegable, opinión abierta, radio y matrices de opciones o minutos.
- Cada opción puede tener puntuación o quedar sin evaluar. Las respuestas informativas se exportan, pero no entran en el resumen estadístico.
- Rangos iniciales editables: 1,00–1,99 Incipiente; 2,00–2,99 En desarrollo; 3,00–4,00 Generado.
- Las preguntas pueden usar puntuación inversa, ser obligatorias u opcionales y admitir una respuesta «Otra».
- Las respuestas críticas de autolesión generan una alerta visible para tutoría/administración designada y con autorización específica con estado y notas de revisión; nunca se envían por correo.
- Excel contiene todas las respuestas; PDF ofrece informe de curso y ficha individual.
- Las respuestas históricas de los documentos de referencia no se importan por privacidad.
- El enlace RGPD se muestra en acceso y pie de página.
- Google OAuth queda preparado mediante variables de entorno; antes del despliegue hay que registrar la URL final de callback en Google Cloud.

La guía de privacidad y actualización enlazada arriba prevalece sobre las instrucciones de despliegue anteriores.

## Actualización de una instalación existente

```bash
git pull
source ~/.virtualenvs/autopercepcion-env/bin/activate
python -m pip install -r requirements.txt
python -m flask --app backend.app db upgrade
python -m flask --app backend.app seed-data
cd frontend && npm ci && npm run build
```

Antes de ejecutar estos pasos, seguir la copia de seguridad y revisión de cuentas descritas en la guía. Después hay que recargar la aplicación web. El administrador debe asignar los formularios publicados a cada curso desde **Administración > Cursos**.
