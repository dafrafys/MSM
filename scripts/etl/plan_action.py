import os
import pandas as pd

def load_plan_actions():
    path = os.getenv('PLAN_ACTIONS_PATH')

    if not path:
        print("La variable d'environnement 'PLAN_ACTIONS_PATH' n'est pas définie.")
        return pd.DataFrame()

    try:
        df = pd.read_excel(path, sheet_name='Suivi analyses')
        if not df.empty:
            print(f"Fichier chargé avec succès : {len(df)} lignes disponibles.")
        else:
            print("Fichier chargé mais aucune donnée trouvée.")
        return df
    except FileNotFoundError:
        print(f"Fichier Excel non trouvé à {path}, chargement ignoré temporairement.")
        return pd.DataFrame() # ou une structure adaptée à ton usage
