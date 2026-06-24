import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "scripts")))

load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    env = os.getenv("APP_ENV", "prod")
    debug_mode = os.getenv("DEBUG", str(env == "dev")).lower() in ("true", "1", "yes")
    port = int(os.getenv("PORT", 5000))

    host = os.getenv("FLASK_RUN_HOST")
    if not host:
        host = "0.0.0.0" if env != "dev" else "127.0.0.1"

    print(f"=== Démarrage Flask - ENV [{env.upper()}] sur http://{host}:{port} ===")
    try:
        app.run(debug=debug_mode, host=host, port=port)
    except Exception as e:
        print(f"Erreur au démarrage de l'app : {e}")
