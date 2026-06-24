# scripts/etl/impact_finissage.py

import sys
from scripts.etl.common import log_info
from scripts.etl.extract import extract_impact_finissage
from scripts.etl.transform import transform_impact_finissage
from scripts.etl.load import load_impact_finissage

def main(session_id: int, excel_arg: str=None):
    log_info(f"=== Début ETL Impact Finissage (Session={session_id}) ===")
    # 1) Extract
    df_brut=extract_impact_finissage(excel_arg)

    # 2) Transform
    df_ready=transform_impact_finissage(df_brut)

    # 3) Load
    load_impact_finissage(df_ready)
    log_info("=== Fin ETL Impact Finissage ===")

if __name__=='__main__':
    if len(sys.argv)<2:
        print('Usage: python -m scripts.etl.impact_finissage <Session_Id> [<Excel_ARG>]')
        sys.exit(1)
    sid=int(sys.argv[1])
    arg=sys.argv[2] if len(sys.argv)>2 else None
    main(sid,arg)
