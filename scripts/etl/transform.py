# scripts/etl/transform.py

import pandas as pd
from datetime import timedelta
from datetime import datetime, date
from scripts.etl.common import get_grouped_columns, SERVICE_MAP, log_info, filter_current_month, valeur_fysol, normaliser_nom, flatten_multiindex_columns


def transform_bbs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie et prépare le DataFrame brut des BBS :
    - Filtre sur le mois en cours (date BBS).
    - Jointure sur le référentiel 'Personnel' via normaliser_nom.
    - Construit le DataFrame final [Personnel_Id, Date_BBS, Description].
    """
    log_info("Transform (BBS) : début du nettoyage et du mapping sur Personnel")

    if df.empty:
        return df

    # 1) S'assurer que Date_BBS est au format datetime
    df["Date_BBS"] = pd.to_datetime(df["Date_BBS"], errors="coerce")
    aujourdhui = date.today()
    # 2) Filtrer sur l'année et le mois en cours
    df = df.loc[
        (df["Date_BBS"].dt.year  == aujourdhui.year) &
        (df["Date_BBS"].dt.month == aujourdhui.month)
    ].copy()
    if df.empty:
        log_info(f"Transform (BBS) : aucun BBS pour {aujourdhui.month}/{aujourdhui.year}")
        return df

    # 3) Charger le référentiel Personnel depuis la base
    from scripts.etl.common import get_sqlalchemy_engine
    engine = get_sqlalchemy_engine()
    pers = pd.read_sql('SELECT "Personnel_Id", "Nom", "Prenom" FROM "Personnel";', engine)

    # 4) Construire la clé normalisée pour le référentiel
    pers["cle"] = (pers["Nom"] + " " + pers["Prenom"]).map(normaliser_nom)
    # 5) Construire la clé normalisée pour les BBS extraits
    df["cle"] = df["Personne"].map(normaliser_nom)

    # 6) Jointure interne : ne garder que ceux qui matchent le référentiel
    df = df.merge(pers[["Personnel_Id", "cle"]], on="cle", how="inner")
    if df.empty:
        log_info("Transform (BBS) : aucun nom ne correspond au référentiel Personnel")
        return df

    # 7) Construire le sous-ensemble final
    df_final = df[["Personnel_Id", "Date_BBS", "Description"]].copy()

    log_info(f"Transform (BBS) : {len(df_final)} ligne(s) prêtes à charger")
    return df_final

def transform_accidents(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie et prépare le DataFrame des accidents :
    - Renommage des colonnes selon la convention interne.
    - Conversion des mois textuels en nombres via mois_map.
    - Construction de la colonne 'Date_Acc' à partir de Date Year/Mois/Jour/Heure.
    - Filtrage des lignes sans valeurs critiques.
    - Standardisation de quelques champs (Classe_Acc, Status_Acc, Service_Acc).
    - Retourne un sous-ensemble de colonnes prêtes pour le chargement.
    """
    log_info("Transform (Accidents) : début du nettoyage et des calculs")

    # 1) Renommage des colonnes pour simplifier
    df.rename(
        columns={
            "N° Accident": "Accident_Id",
            "Type AT": "Type_Acc",
            "Atelier": "Secteur_Acc",
            "Position/ N° machine": "Equipement",
            "Date Année": "Date_Year",
            "Date Mois": "Date_Month",
            "Date Jour": "Date_Day",
            "Circonstances": "Description_Acc",
            "DU Classes de risques": "Classe_Acc",
            "Etat Analyse": "Status_Acc",
            "Unité de travail DU à laquelle l'employé est rattachée": "Service_Acc"
        },
        inplace=True
    )

    # 2) Mettre la 'Classe_Acc' en majuscules
    df["Classe_Acc"] = df["Classe_Acc"].astype(str).str.upper()

    # 3) Mapping des mois français vers entiers
    mois_map = {
        "Janvier": 1, "Février": 2, "Mars": 3, "Avril": 4,
        "Mai": 5, "Juin": 6, "Juillet": 7, "Août": 8,
        "Septembre": 9, "Octobre": 10, "Novembre": 11, "Décembre": 12
    }
    df["Date_Month"] = df["Date_Month"].astype(str).str.strip().str.capitalize()
    df["Date_Month"] = df["Date_Month"].map(mois_map)

    # 4) Conversion des colonnes Date_Year, Date_Month, Date_Day en entiers
    df["Date_Year"]  = pd.to_numeric(df["Date_Year"], errors="coerce").astype("Int64")
    df["Date_Month"] = pd.to_numeric(df["Date_Month"], errors="coerce").astype("Int64")
    df["Date_Day"]   = pd.to_numeric(df["Date_Day"], errors="coerce").astype("Int64")

    # 5) Suppression des lignes sans date complète ou heure
    df = df.dropna(subset=["Date_Year", "Date_Month", "Date_Day", "Heure"])

    # **Ajoute cette ligne pour faire une copie indépendante**
    df = df.copy()

    # 6) Construction de chaînes de date/heure pour parsing
    df["Year_str"]  = df["Date_Year"].astype(int).astype(str)
    df["Month_str"] = df["Date_Month"].astype(int).astype(str).str.zfill(2)
    df["Day_str"]   = df["Date_Day"].astype(int).astype(str).str.zfill(2)

    # 7) Normalisation de la colonne Heure vers un format "HH:MM"
    df["Heure_str"] = df["Heure"].str.replace("h", ":", regex=False)
    df["Heure_str"] = df["Heure_str"].apply(lambda h: h if ":" in h else f"{h}:00")

    # 8) Concaténation en une seule chaîne puis conversion en datetime
    df["temp_date_str"] = (
        df["Year_str"] + "-" +
        df["Month_str"] + "-" +
        df["Day_str"] + " " +
        df["Heure_str"]
    )
    df["Date_Acc"] = pd.to_datetime(
        df["temp_date_str"],
        format="%Y-%m-%d %H:%M",
        errors="coerce"
    )

    # 9) Supprimer les lignes sans 'Secteur_Acc'
    df = df.dropna(subset=["Secteur_Acc"])

    # 10) Supprimer toutes les lignes qui n’ont pas (Date_Acc, Secteur_Acc, Description_Acc)
    df = df.dropna(subset=["Date_Acc", "Secteur_Acc", "Description_Acc"])

    # 11) Nettoyage de 'Classe_Acc' : suppression éventuelle de premiers chiffres/pointage
    df["Classe_Acc"] = df["Classe_Acc"].str.replace(r"^\d+\.\s*", "", regex=True)

    # 12) Supprimer les colonnes temporaires utilisées pour construire la date
    df.drop(
        ["Year_str", "Month_str", "Day_str", "Heure_str", "temp_date_str"],
        axis=1,
        inplace=True
    )

    # 13) Mise au propre de 'Description_Acc' : trim et suppression des multiples espaces
    df["Description_Acc"] = (
        df["Description_Acc"]
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # 14) Remplir 'Status_Acc' vide par "NON ANALYSÉ"
    df["Status_Acc"] = df["Status_Acc"].fillna("NON ANALYSÉ")

    # 15) Simplifier 'Service_Acc' : si commence par "Maintenance", on le normalise
    df["Service_Acc"] = df["Service_Acc"].apply(
        lambda val: "Maintenance" if isinstance(val, str) and val.startswith("Maintenance") else val
    )

    # 16) Construction du sous-ensemble final des colonnes
    columns_to_transfer = [
        "Type_Acc", "Date_Acc", "Secteur_Acc",
        "Description_Acc", "Service_Acc", "Status_Acc",
        "Classe_Acc"
    ]
    df_subset = df[columns_to_transfer].copy()

    log_info(f"Transform (Accidents) : {len(df_subset)} lignes prêtes pour le chargement")
    return df_subset

def transform_impact_fibrage(df: pd.DataFrame) -> pd.DataFrame:
    log_info("Transformation : début nettoyage et calculs")

    # 1) Identification des groupes de colonnes
    df = flatten_multiindex_columns(df)
    av_cols, eq_cols, svc_cols = get_grouped_columns(df)

    # 2) Mapping des colonnes de base
    col_map = {
        "Date":        "DONNEES DE BASE > Date",
        "Equipe":      "DONNEES DE BASE > Equipe",
        "Poste":       "DONNEES DE BASE > Poste",
        "Type_Perte":  "DONNEES DE BASE > Type de perte",
        "Temps_Arret": "DONNEES CHIFFREES > Temps d'arret (min)",
        "Perte_kg":    "DONNEES CHIFFREES > Perte (kg)",
        "Nb_Filieres": "DONNEES CHIFFREES > Nb filière(s) impactée(s)"
    }
    missing = [v for v in col_map.values() if v not in df.columns]
    if missing:
        raise KeyError(f"Colonnes manquantes dans le fichier : {missing}")

    # 3) Création des colonnes de base
    df["Date_Imp"]   = pd.to_datetime(df[col_map["Date"]], dayfirst=True, errors="coerce")
    df["Equipe_Imp"] = df[col_map["Equipe"]]
    df["Poste_Imp"]  = df[col_map["Poste"]]
    df["Type_Perte"] = df[col_map["Type_Perte"]]

    # 4) Conversion en entier des minutes d'arrêt
    temps_num = pd.to_numeric(df[col_map["Temps_Arret"]], errors="coerce").fillna(0).astype(int)
    df["Temps_Arr_Imp"] = temps_num.apply(lambda m: timedelta(minutes=m))

    # 5) Gestion du nombre de filières
    nbf = pd.to_numeric(df[col_map["Nb_Filieres"]], errors="coerce")
    nbf = nbf.fillna(1).astype(int)
    df["Nb_Filieres"] = pd.Series(nbf, dtype="Int64")

    # 6) Calcul métier de la perte (kg)
    df["Pertes_Impact"] = ((temps_num / 60) * valeur_fysol() * nbf).round(2)

    # 7) Filtrer sur l’année/mois en cours et types de perte
    df = filter_current_month(df, "Date_Imp", "Type_Perte")

    # 8) Description et numéro de ligne Excel
    comment_col = [c for c in df.columns if c.endswith("Commentaires")][0]
    df["Description_Imp"] = df[comment_col]
    df["Excel_row"]      = df.index + 7  # +7 car skiprows=4 et header=2 lignes ?

    # 9) Création des colonnes à plat
    df["Secteur_Imp"] = "Fibrage"
    df["Equipements"] = df[eq_cols].apply(
        lambda r: ",".join(sorted(str(x).strip() for x in r if pd.notna(x) and str(x).strip())),
        axis=1
    )
    df["AVCs"] = df[av_cols].apply(
        lambda r: ",".join(sorted(str(x).strip() for x in r if pd.notna(x) and str(x).strip())),
        axis=1
    )
    df["Services"] = df[svc_cols].apply(
        lambda r: ",".join(sorted({
            SERVICE_MAP.get(c.split(">")[-1].strip(), "A_DEFINIR")
            for c, v in r.items()
            if pd.notna(v) and ((isinstance(v, (int, float)) and v>0) or str(v).strip())
        })),
        axis=1
    )

    df = df.reset_index(drop=True)
    log_info(f"Transformation : terminé, {len(df)} lignes retenues pour chargement")
    return df

def transform_impact_finissage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplati et nettoie le DataFrame brut:
    - Flatten multi-index
    - Filtrer année/mois courant et types de perte
    - Générer colonnes Date_Imp,Secteur,Type,Equipe,Description,Excel_row
    - Générer flags Ligne_x et Equip_x
    - Préparer les colonnes poids
    """
    log_info("Transform (Impact Finissage) : aplatissement des colonnes")
    print("Colonnes chargées :", df.columns.tolist())

    # Flatten
    df.columns = [
        f"{str(g).strip().upper()} > {str(s).strip().upper()}" if g and s and str(g).strip()!=str(s).strip()
        else (str(g) if g else str(s)).strip().upper()
        for g,s in df.columns
    ]
    print("Colonnes disponibles :", df.columns.tolist())

    # Identify columns
    line_cols = {int(c.split('>')[-1].strip()):c for c in df.columns if c.startswith('LIGNE >')}
    eq_cols   = [c for c in df.columns if c.startswith('EQUIPEMENT >')]
    weight_cols = {c:c.split('>')[-1].strip().capitalize() for c in df.columns if c.startswith('POIDS PAR TYPE DE PERTE EN KG >')}

    # Required
    REQUIRED = {
        'Date':'DÉBUT > DATE',
        'Type':'EQUIPE > TYPE DE PERTE',
        'Equipe': 'EQUIPE',
        'Desc':'² > DESCRIPTIF DE LA PERTE (LONG FILS, FAUSSES COUPES,…)'
    }
    missing = [col for col in REQUIRED.values() if col not in df.columns]
    if missing:
        print("\n*** Colonnes disponibles dans le DataFrame ***")
        for c in df.columns:
            print(f"- {c}")
        print("*** Fin liste colonnes ***\n")

        raise KeyError(f"Colonne requise {missing} manquante")

    # Filter
    df[REQUIRED['Date']]=pd.to_datetime(df[REQUIRED['Date']],dayfirst=True,errors='coerce')
    now=datetime.now()
    df=df[
        (df[REQUIRED['Date']].dt.year==now.year)&
        (df[REQUIRED['Date']].dt.month==now.month)&
        (df[REQUIRED['Type']].isin(["Panne","Maintenance planifiée"]))
    ].dropna(subset=[REQUIRED['Date']])

    # Base columns
    df['Date_Imp']=df[REQUIRED['Date']].dt.date
    df['Secteur_Imp']='Finissage'
    df['Type_de_Perte']=df[REQUIRED['Type']]
    df['Equipe_Imp'] = df[REQUIRED['Equipe']]   # ou colonne dédiée
    df['Description_Imp']=df[REQUIRED['Desc']]
    df['Excel_row']=df.index+4

    # Ligne flags
    for idx,col in line_cols.items():
        df[f'Ligne_{idx}']=(df[col].astype(str).str.upper().eq('X')).astype(int)
    # Equip flags
    for col in eq_cols:
        key=col.split('>')[-1].strip().replace(' ','_')
        df[f'Equip_{key}']=(df[col].astype(str).str.upper().eq('X')).astype(int)
    # weight numeric
    for full in weight_cols.keys():
        df[full]=pd.to_numeric(df[full],errors='coerce').fillna(0)

    log_info(f"Transform : {df.shape[0]} lignes prêtes")
    return df
