# scripts/etl/accidents.py

import sys
from scripts.etl.common     import log_info
from scripts.etl.extract    import extract_accidents
from scripts.etl.transform  import transform_accidents
from scripts.etl.load       import load_accidents

def main(session_id: int):
    """
    Orchestrateur pour l'ETL Accidents :
    1) extract_accidents()   -> DataFrame brut
    2) transform_accidents() -> DataFrame nettoyé (colonnes finales)
    3) load_accidents()      -> insertion en base
    """
    log_info("=== Début ETL Accidents ===")

    # 1) Extract
    df_brut  = extract_accidents()

    # 2) Transform
    df_ready = transform_accidents(df_brut)

    # 3) Load
    load_accidents(session_id, df_ready)
    log_info("=== Fin ETL Accidents ===")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.etl.accidents <Session_Id>")
        sys.exit(1)
    sid = int(sys.argv[1])
    main(sid)
