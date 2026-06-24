# scripts/etl/common.py

import os
import pandas as pd
import pyodbc
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import unicodedata
import re

# 1) Charger les variables d'environnement depuis un fichier .env (si présent).
#    Cela permet de récupérer DATABASE_URI, ODBC_CONN_STRING, etc., sans les coder en dur.
from dotenv import load_dotenv
load_dotenv()  # Lit automatiquement le fichier ~/.env ou .env à la racine du projet

def get_env():
    """Renvoie l'environnement courant ('prod', 'dev')."""
    return os.getenv("APP_ENV", "prod").lower()

def get_database_uri():
    env = get_env()
    var = f"SQLALCHEMY_DATABASE_URI_{env.upper()}"
    uri = os.getenv(var)
    if not uri:
        raise ValueError(f"Variable {var} non définie dans .env")
    return uri

def get_sqlalchemy_engine():
    """
    Crée et retourne un moteur SQLAlchemy à partir de la variable selon l'env.
    """
    db_uri = get_database_uri()  # Cette fonction renvoie la variable PROD ou DEV
    return create_engine(db_uri)

def get_path(key_base):
    """Renvoie le chemin de fichier adapté à l'env (ex: key_base='FIBRAGE_XLSX')."""
    env = get_env()
    var = f"{key_base}_{env.upper()}"
    val = os.getenv(var)
    if not val:
        raise ValueError(f"Variable {var} non définie dans .env")
    return val

def get_pyodbc_connection():
    """
    Crée et retourne une connexion pyodbc vers SQL Server (ou autre base via ODBC),
    en utilisant la variable d'environnement ODBC_CONN_STRING.
    - Si ODBC_CONN_STRING n'est pas définie, lève une erreur.
    - Utile pour exécuter des requêtes via pyodbc quand on ne passe pas par SQLAlchemy.
    """
    conn_str = os.getenv("ODBC_CONN_STRING", "").strip()
    if not conn_str:
        raise ValueError("ODBC_CONN_STRING non définie. Veuillez la configurer dans votre .env")
    # pyodbc.connect ouvre une connexion ODBC ; timeout=10 secondes par défaut
    return pyodbc.connect(conn_str, timeout=10)


def log_info(msg: str):
    """
    Affiche un message de log au format [YYYY-MM-DD HH:MM:SS] <msg>.
    - Pratique pour tracer l'exécution des ETL en console ou rediriger vers un fichier log.
    - N'utilise pas de librairie lourde, juste print + datetime.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")


# 5) SERVICE_MAP : mapping métier des noms complets vers des codes courts
#    par exemple "Mécanique" → "MECA", "Electricité" → "ELEC", etc.
#    Utilisé dans les ETL (ex. pour construire la colonne "Services").
SERVICE_MAP = {
    "Mécanique":            "MECA",
    "Utilités":             "UTIL",
    "ATF":                  "ATF",
    "Electricité":          "ELEC",
    "Autom - Supervisions": "AUTOM",
    "IT":                   "IT",
    "Process":              "PROCESS"
}


def flatten_multiindex(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplati un DataFrame dont le header comporte deux niveaux (MultiIndex).
    Concatène les deux niveaux par "groupe > sous-groupe" sauf si l'un des niveaux est vide.
    Par exemple, si on a un Excel avec header sur deux lignes, cette fonction permet de
    créer des noms de colonnes lisibles :
      - ("AVANT-CORPS", "Position")  → "AVANT-CORPS > Position"
      - ("DONNEES DE BASE", "Date") → "DONNEES DE BASE > Date"
    - df.columns.map(...) parcourt chaque tuple (groupe, sous-groupe).
    - On renvoie le même DataFrame avec les colonnes renommées.
    """
    new_cols = []
    for g, s in df.columns.map(lambda x: (str(x[0]).strip(), str(x[1]).strip())):
        if g and s and g != s:
            # Si on a un groupe et un sous-groupe, et qu'ils sont différents
            new_cols.append(f"{g} > {s}")
        else:
            # Si l'un des deux est vide, on prend celui qui n'est pas vide
            new_cols.append(g or s)
    df.columns = new_cols
    return df


def get_grouped_columns(df: pd.DataFrame):
    """
    Recherche dans les colonnes du DataFrame les colonnes qui commencent par :
      - "AVANT-CORPS >"
      - "EQUIPEMENT >"
      - "Suivi Maintenance >"
    et renvoie trois listes (av_cols, eq_cols, svc_cols).
    Utile pour séparer dynamiquement les colonnes d’équipement, d’AVC, de services, etc.
    """
    av_cols  = [c for c in df.columns if c.startswith("AVANT-CORPS >")]
    eq_cols  = [c for c in df.columns if c.startswith("EQUIPEMENT >")]
    svc_cols = [c for c in df.columns if c.startswith("Suivi Maintenance >")]
    return av_cols, eq_cols, svc_cols


def valeur_fysol() -> float:
    """
    Calcule la "valeur fysol" utilisée dans le calcul des pertes (en kg/h, par ex.).
    Formule métier : (2950 * 0.9 / 24) * 0.97
    - 2950 : débit nominal
    - 0.9 / 24 : coefficient horaire
    - 0.97 : coefficient de rendement
    Vous pouvez ajuster ce calcul selon la charte métier.
    """
    return (2950 * 0.9 / 24) * 0.97


def filter_current_month(df: pd.DataFrame, date_col: str, type_col: str) -> pd.DataFrame:
    """
    Filtre le DataFrame pour ne garder que les lignes dont :
      - la date dans `date_col` est dans l'année et le mois courant,
      - et la valeur dans `type_col` appartient à ["Panne", "Maintenance planifiée"].

    - date_col : nom de la colonne contenant un datetime (p. ex. "Date_Imp").
    - type_col : nom de la colonne contenant le type de perte (p. ex. "Type_Perte").
    Renvoie une copie (DataFrame filtré + suppression des NaN sur date_col).
    """
    now = datetime.now()
    mask = (
        (df[date_col].dt.year  == now.year) &
        (df[date_col].dt.month == now.month) &
        (df[type_col].isin(["Panne", "Maintenance planifiée"]))
    )
    # dropna(subset=[date_col]) : on supprime toute ligne dont la date est NaN
    return df.loc[mask].dropna(subset=[date_col]).copy()

def normaliser_nom(nom: str) -> str:
    """
    Normalise un nom :
    - Retire les espaces avant/après
    - Met en majuscule
    - Retire les accents
    - Retire les caractères spéciaux (optionnel)
    """
    if not isinstance(nom, str):
        return ""
    nom = nom.strip()
    nom = nom.upper()
    nom = ''.join(
        c for c in unicodedata.normalize('NFD', nom)
        if unicodedata.category(c) != 'Mn'
    )
    # Supprimer espaces multiples
    nom = re.sub(r'\s+', ' ', nom)
    # Supprimer caractères spéciaux (optionnel)
    #nom = re.sub(r'[^A-Z0-9 ]', '', nom)
    return nom

def flatten_multiindex_columns(df):
    df.columns = [' > '.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in df.columns]
    return df
