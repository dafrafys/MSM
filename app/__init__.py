# app/__init__.py
 #  Enregistre tes blueprints adapte à tes blueprints
import logging
import os
from flask import Flask
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy import text

from .extensions import db, get_raw_engine
from app.blueprints.home import bp as home_bp
from app.blueprints.services import bp as services_bp
from app.blueprints.common import common_bp
from app.blueprints.action import bp as action_bp

# ... autres blueprints


def create_app():
    app = Flask(__name__)

    # Exemple : charger config selon l'env # Récupère la variable d’environnement pour choisir la config (prod/dev)
    env = os.getenv("APP_ENV", "prod")
    if env == "dev":
        app.config.from_object("app.config.DevConfig")
    else:
        app.config.from_object("app.config.ProdConfig")

    # Configuration du logging selon le mode debug
    debug_mode = app.config.get("DEBUG", False)
    if debug_mode:
        app.logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
        app.logger.debug("Mode DEBUG activé : niveau de log DEBUG")
    else:
        app.logger.setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.INFO)
    # Log de la chaîne de connexion utilisée (important pour debug)
    app.logger.info(f"Using SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

    # 2. Initialiser les extensions
    db.init_app(app)

    # 3. Enregistrer les blueprints
    app.register_blueprint(home_bp,      url_prefix="")
    app.register_blueprint(services_bp, url_prefix='/services')
    app.register_blueprint(common_bp, url_prefix="/common")
    app.register_blueprint(action_bp, url_prefix='/action')


    # 4. Filtres Jinja partagés
    @app.template_filter("format_interval")
    def format_interval(interval):
        if not interval:
            return "–"
        return f"{int(interval.total_seconds() // 60)} min"

    # Charge SERVICE_LABELS depuis la base
    with app.app_context():
        engine = get_raw_engine()
        try:
            with engine.connect() as conn:
                rows = conn.execute(
                    text('SELECT "Service_code", "service_label" FROM "Service_maint"')
                ).fetchall()
            app.config['SERVICE_LABELS'] = {
                r.Service_code.lower(): r.service_label   # clé en minuscules
                for r in rows
            }
        except (ProgrammingError, OperationalError):
            # La table n'existe pas encore ➜ on démarre quand même
            app.logger.warning("Table Service_maint absente ; labels non chargés.")
            app.config['SERVICE_LABELS'] = {}

    return app
