from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from database import db


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    CORS(app, resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})
    JWTManager(app)

    # Init DB
    db.init_app(app)
    with app.app_context():
        try:
            db.engine.connect().close()
        except Exception as exc:
            app.logger.warning("Database not reachable: %s", exc)

    # Deferred imports to avoid circular deps
    from api.all import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)

