# scripts/etl/bbs.py

import sys
from scripts.etl.common    import log_info
from scripts.etl.extract   import extract_bbs
from scripts.etl.transform import transform_bbs
from scripts.etl.load      import load_bbs
import os


def main(session_id: int = 1):
    """
    Orchestrateur pour l'ETL BBS :
    1) extract_bbs()   -> DataFrame brut [Personne, Date_BBS, Description]
    2) transform_bbs() -> DataFrame [Personnel_Id, Date_BBS, Description]
    3) load_bbs()      -> insertion dans BBS_Stat
    """
    log_info("=== Début ETL BBS ===")

    # 1) Extract
    df_brut  = extract_bbs(fallback_dir=os.path.abspath(os.path.join(__file__, "../../data")))

    # 2) Transform
    df_ready = transform_bbs(df_brut)

    # 3) Load
    load_bbs(session_id, df_ready)
    log_info("=== Fin ETL BBS ===")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m scripts.etl.bbs <Session_Id>")
        sys.exit(1)
    sid = int(sys.argv[1])
    main(sid)
