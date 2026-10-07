import hashlib
import hmac
import time

import click
from flask import jsonify, render_template_string, request
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from .extensions import db, jwt
from .models import AuthAttempt, User


def limit_auth_attempts(app):
    """Shared database counters, containing no raw email addresses or IPs."""
    now = int(time.time())
    window = now // 900
    expires = (window + 1) * 900
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error="Solicitud no válida."), 400
    email = str(data.get("email", "")).strip().lower()
    identities = [("ip:" + (request.remote_addr or "unknown"), 200)]
    if email:
        identities.append(("email:" + email, 10))
    db.session.execute(delete(AuthAttempt).where(AuthAttempt.expires_at <= now))
    exceeded = False
    for identity, maximum in identities:
        key = hmac.new(app.config["SECRET_KEY"].encode(), f"{window}:{request.path}:{identity}".encode(), hashlib.sha256).hexdigest()
        increment = update(AuthAttempt).where(AuthAttempt.key == key).values(hits=AuthAttempt.hits + 1)
        if not db.session.execute(increment).rowcount:
            try:
                with db.session.begin_nested():
                    db.session.add(AuthAttempt(key=key, hits=1, expires_at=expires))
                    db.session.flush()
            except IntegrityError:
                db.session.execute(increment)
        exceeded |= db.session.get(AuthAttempt, key).hits > maximum
    db.session.commit()
    if exceeded:
        response = jsonify(error="Demasiados intentos. Espera unos minutos antes de volver a intentarlo.")
        response.status_code = 429
        response.headers["Retry-After"] = str(expires - now)
        return response


def register_security(app):
    @app.cli.command("purge-auth-attempts")
    def purge_auth_attempts():
        """Remove expired pseudonymous authentication counters."""
        result = db.session.execute(delete(AuthAttempt).where(AuthAttempt.expires_at <= int(time.time())))
        db.session.commit()
        click.echo(f"Contadores caducados eliminados: {result.rowcount}")

    @jwt.token_in_blocklist_loader
    def revoked(_header, payload):
        try:
            user = db.session.get(User, int(payload["sub"]))
        except (ValueError, TypeError, KeyError):
            return True
        return not user or not user.is_active or not user.is_verified or payload.get("version") != user.auth_version

    @app.before_request
    def protect_legacy_health_routes():
        if request.endpoint in {"api.questionnaire", "api.submit_attempt", "api.attempts", "api.analytics", "api.export_course"}:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
            from .privacy import require_sensitive_access
            require_sensitive_access()

    @app.before_request
    def protect_mutations():
        if request.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            # A custom header cannot be sent by a cross-origin HTML form.
            if request.headers.get("X-Requested-With") != "XMLHttpRequest":
                return jsonify(error="Solicitud no válida."), 403
            origin = request.headers.get("Origin")
            if origin and origin not in (app.config["FRONTEND_URL"], app.config["BACKEND_URL"]):
                return jsonify(error="Origen no autorizado."), 403
            if request.path in ("/api/auth/login", "/api/auth/register"):
                return limit_auth_attempts(app)

    @app.after_request
    def private_response(response):
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith("/api/") or request.path == "/privacidad":
            response.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/privacidad")
    def privacy():
        fields = [(label, app.config[key]) for label, key in (
            ("Responsable", "PRIVACY_CONTROLLER"), ("Contacto y derechos", "PRIVACY_CONTACT"),
            ("Base jurídica", "PRIVACY_LEGAL_BASIS"), ("Conservación", "PRIVACY_RETENTION"),
            ("Proveedores, ubicación y transferencias", "PRIVACY_PROVIDERS"),
        )]
        return render_template_string('''<!doctype html><html lang="es"><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Privacidad · Cuestionarios</title><main style="max-width:55rem;margin:2rem auto;padding:1rem;font:1.1rem/1.6 system-ui">
        <h1>Privacidad · Cuestionarios</h1>
        {% if incomplete %}<p><strong>Información pendiente de completar y validar por el centro antes de su uso con alumnado.</strong></p>{% endif %}
        <p>Esta herramienta recoge nombre, correo, pertenencia a cursos, respuestas educativas, posibles datos de salud, resultados y notas de revisión para apoyar la orientación educativa.</p>
        <p>El alumnado consulta sus resultados. Las personas tutoras acceden a sus cursos asignados y la administración gestiona las cuentas y los cursos.</p>
        <p>Los datos sensibles requieren autorización específica del centro y personas revisoras designadas. Las exportaciones deben permanecer en los destinos institucionales autorizados.</p>
        <p>Los resultados y alertas se calculan mediante reglas. Requieren revisión humana; no constituyen un diagnóstico ni un servicio de emergencia. El centro debe explicar quién revisa las alertas, en qué plazo y qué canal de ayuda usar.</p>
        {% for label, value in fields %}<h2>{{ label }}</h2><p>{{ value or 'Pendiente de definición por el centro.' }}</p>{% endfor %}
        <p>Puedes solicitar información, acceso, rectificación, supresión y los demás derechos que correspondan a través del contacto indicado, y presentar una reclamación ante la AEPD.</p>
        <p>El acceso con Google utiliza Google como proveedor de identidad. La sesión utiliza cookies necesarias para autenticación y protección frente a solicitudes fraudulentas.</p>
        </main></html>''', fields=fields, incomplete=any(not value for _, value in fields))
