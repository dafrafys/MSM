# scripts/etl/__init__.py

"""
Package ETL pour Huddle :
- extract   : lecture des sources (Excel, CSV…)
- transform : nettoyage / calculs métiers
- load      : insertion en base
- orchestrateurs : fichiers CLI pour lancer chaque flux
"""

# Version du package (facultatif)
__version__ = "0.1.0"

# Exposer par défaut les modules et fonctions les plus utilisés
from .extract   import extract_impact_fibrage, extract_bbs, extract_accidents, extract_impact_finissage
from .transform import transform_impact_fibrage, transform_bbs, transform_accidents, transform_impact_finissage
from .load      import load_impact_fibrage, load_bbs, load_accidents, load_impact_finissage

# Si vous créez d'autres orchestrateurs, vous pouvez aussi les importer ici
# from .main_courante      import main as run_main_courante
# from .impact_fibrage     import main as run_impact_fibrage
# from .impact_finissage   import main as run_impact_finissage
# from .accidents          import main as run_bbs

__all__ = [
    "extract_accidents", "extract_impact_fibrage", "extract_bbs", "extract_impact_finissage",
    "transform_accidents", "transform_impact_fibrage", "transform_bbs", "transform_impact_finissage",
    "load_accidents", "load_impact_fibrage", "load_bbs", "load_impact_finissage",
    "update_bbs_source",
    # "run_main_courante", "run_impact_fibrage", "run_impact_finissage", "run_bbs"
]
