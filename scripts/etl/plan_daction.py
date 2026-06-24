import pandas as pd

def load_plan_actions():
    try:
        df = pd.read_excel('/mnt/q/TPM/4 - Piliers/3 - Maintenance Planifiée (PM)/9 - Analyses de panne/Suivi Analyses de panne.xlsx', sheet_name='Suivi analyses')
        return df
    except FileNotFoundError:
        # Fichier absent, on log et on retourne un DataFrame vide ou autre valeur par défaut
        print("Fichier Excel non trouvé, chargement ignoré temporairement.")
        return pd.DataFrame()  # ou une structure adaptée à ton usage
