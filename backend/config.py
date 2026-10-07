import os
from pathlib import Path
from dotenv import load_dotenv


def config_values():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    values = {key: os.getenv(key, "") for key in (
        "SECRET_KEY", "JWT_SECRET_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
        "MAIL_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_DEFAULT_SENDER",
        "RETENTION_DAYS", "PRIVACY_CONTROLLER", "PRIVACY_CONTACT", "PRIVACY_LEGAL_BASIS",
        "PRIVACY_RETENTION", "PRIVACY_PROVIDERS",
    )}
    values.update(
        JWT_ACCESS_TOKEN_EXPIRES=7200,
        JWT_TOKEN_LOCATION=["cookies"], JWT_COOKIE_CSRF_PROTECT=True,
        JWT_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() == "true",
        JWT_COOKIE_SAMESITE="Lax", JWT_ACCESS_COOKIE_PATH="/api/",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() == "true",
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL") or "sqlite:///autopercepcion.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        AUTO_CREATE_DB=False,
        FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:4200").rstrip("/"),
        BACKEND_URL=os.getenv("BACKEND_URL", "http://localhost:5000").rstrip("/"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "587")), MAIL_USE_TLS=True, MAIL_DEBUG=False,
        SENSITIVE_DATA_ENABLED=os.getenv("SENSITIVE_DATA_ENABLED", "false").lower() == "true",
    )
    for key in ("ADMIN_EMAILS", "REGISTRATION_EMAILS", "SENSITIVE_REVIEWER_EMAILS"):
        values[key] = {email.strip().lower() for email in os.getenv(key, "").split(",") if email.strip()}
    return values
