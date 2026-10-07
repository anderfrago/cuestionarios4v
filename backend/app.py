from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from dotenv import load_dotenv
from .config import config_values
from .extensions import cors, db, jwt, mail, migrate, oauth
from .routes import api
from .forms import forms
from .seed import seed_questionnaires


def create_app(config=None):
    load_dotenv()

    static_dir = (
        Path(__file__).resolve().parent.parent
        / "frontend"
        / "dist"
        / "autopercepcion"
        / "browser"
    )

    app = Flask(__name__, static_folder=None)
    app.config.update(config_values())
    if config: app.config.update(config)
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
        value = app.config.get(key, "")
        if len(value) < 32 or any(word in value.lower() for word in ("cambia", "dev-change", "desarrollo")):
            raise RuntimeError(f"Configura {key} con una clave aleatoria de al menos 32 caracteres")
    db.init_app(app); migrate.init_app(app, db); jwt.init_app(app); mail.init_app(app); oauth.init_app(app)
    if app.config.get("GOOGLE_CLIENT_ID"):
        oauth.register(name="google", client_id=app.config["GOOGLE_CLIENT_ID"],
                       client_secret=app.config["GOOGLE_CLIENT_SECRET"],
                       server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                       client_kwargs={"scope": "openid email profile"})
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["FRONTEND_URL"]}}, supports_credentials=True)
    app.register_blueprint(api)
    app.register_blueprint(forms)
    from .security import register_security
    from .retention import register_retention
    register_security(app)
    register_retention(app)

    @app.errorhandler(404)
    def not_found(_): return jsonify(error="Recurso no encontrado"), 404

    @app.errorhandler(403)
    def forbidden(error): return jsonify(error=getattr(error, "description", "Acceso denegado")), 403

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path=""):
        if path.startswith("api/"):
            return jsonify(error="Recurso no encontrado"), 404

        candidate = static_dir / path

        if path and candidate.is_file():
            return send_from_directory(static_dir, path)

        index_file = static_dir / "index.html"

        if index_file.is_file():
            return send_from_directory(static_dir, "index.html")

        return jsonify(
            message="Frontend no compilado. Ejecuta npm run build en frontend/"
        ), 503

    @app.cli.command("seed-data")
    def seed_data_command():
        """Carga los cuestionarios iniciales sin duplicarlos."""
        seed_questionnaires()
        print("Datos iniciales cargados")

    with app.app_context():
        if app.config.get("AUTO_CREATE_DB", True):
            db.create_all()
            seed_questionnaires()
    return app
