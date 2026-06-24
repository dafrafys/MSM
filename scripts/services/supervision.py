# scripts/services/supervision.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Charger les variables d'environnement
load_dotenv()

# Créer l'engine SQLAlchemy
sqlserver_uri = os.getenv("SQLSERVER_URI")
if not sqlserver_uri:
    raise RuntimeError("⚠️ SQLSERVER_URI n'est pas défini dans le .env")
engine = create_engine(sqlserver_uri, connect_args={"timeout": 5})

def fetch_supervision():
    query = text("""
        SELECT TOP 10
            OriginationTime,
            TerminationTime,
            MachineType,
            PayLoad,
            name,
            Duration
        FROM T_AlarmConsolidated
        WHERE (priority = 4 OR priority = 3)
          AND PayLoad = ''
        ORDER BY OriginationTime DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()

    return [
        {
            "start": str(r.OriginationTime),
            "end": str(r.TerminationTime),
            "face": r.PayLoad,
            "machine": r.MachineType,
            "description": r.name,
            "duration": format_duration(r.Duration),
        }
        for r in rows
    ]
def format_duration(seconds):
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{int(minutes)}min {int(remaining_seconds)}s"
