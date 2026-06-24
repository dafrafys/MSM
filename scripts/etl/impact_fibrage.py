# scripts/etl/impact_fibrage.py

import sys
from scripts.etl.common import log_info
from scripts.etl.extract import extract_impact_fibrage
from scripts.etl.transform import transform_impact_fibrage
from scripts.etl.load import load_impact_fibrage

def main(session_id: int):
    log_info("=== ETL Impact Fibrage démarré ===")
    # 1) Extract
    df_brut = extract_impact_fibrage()

    # 2) Transform
    df_ready = transform_impact_fibrage(df_brut)

    # 3) Load
    load_impact_fibrage(session_id, df_ready)
    log_info("=== ETL Impact Fibrage terminé ===")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.etl.impact_fibrage <Session_Id>")
        sys.exit(1)
    sid = int(sys.argv[1])
    main(sid)
