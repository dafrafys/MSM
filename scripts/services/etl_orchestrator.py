# scripts/services/etl_orchestrator.py
# (logique d'appel des etl sur une session)
from scripts.etl import impact_fibrage, impact_finissage, bbs, accident
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl.worksheet._reader")


def run_etl_pipeline(session_id):
    """
    Orchestration des différents scripts ETL pour une session donnée.
    """
    # Appel direct en Python natif (privilégié)
    impact_fibrage.main(session_id)
    impact_finissage.main(session_id)
    bbs.main(session_id)
    accident.main(session_id)
    # Si un ETL renvoie un code d’erreur, lève une exception ou retourne un statut
    return True
