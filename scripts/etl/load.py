# scripts/etl/load.py

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from scripts.etl.common import get_sqlalchemy_engine, log_info

def load_bbs(session_id: int, df: pd.DataFrame):
    """
    Charge les données dans BBS_Stat en respectant la liaison vers BBS.
    - Insère un enregistrement dans BBS avec Session_Id.
    - Ajoute la colonne BBS_Id dans df avant insertion dans BBS_Stat.
    - Évite les doublons sur BBS_Stat.
    """
    log_info("Load (BBS) : début de l'insertion en base")

    if df.empty:
        log_info("Load (BBS) : DataFrame vide, rien à insérer")
        return

    engine = get_sqlalchemy_engine()

    with engine.begin() as conn:
        # 1) Insérer la session dans BBS et récupérer BBS_Id
        bbs_id = conn.execute(
            text('INSERT INTO public."BBS" ("Session_Id") VALUES (:sid) RETURNING "BBS_Id"'),
            {'sid': session_id}
        ).scalar_one()

        log_info(f"Load (BBS) : nouveau BBS_Id créé : {bbs_id}")

        # 2) Charger les clés existantes dans BBS_Stat pour éviter doublons
        exist = pd.read_sql(
            'SELECT "Personnel_Id", "Date_BBS", "Description" FROM public."BBS_Stat";',
            conn
        )
        exist["Date_BBS"] = pd.to_datetime(exist["Date_BBS"], errors="coerce")
        df["Date_BBS"] = pd.to_datetime(df["Date_BBS"], errors="coerce")

        # 3) Filtrer les nouvelles entrées
        merged = df.merge(
            exist,
            on=["Personnel_Id", "Date_BBS", "Description"],
            how="left",
            indicator=True
        )
        df_new = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

        if df_new.empty:
            log_info("Load (BBS) : aucune nouvelle entrée à insérer")
            return

        # 4) Ajouter la colonne BBS_Id
        df_new["BBS_Id"] = bbs_id

        # 5) Supprimer Session_Id si présent
        if "Session_Id" in df_new.columns:
            df_new = df_new.drop(columns=["Session_Id"])

        # 6) Insérer dans BBS_Stat
        try:
            df_new.to_sql(
                name="BBS_Stat",
                con=conn,
                if_exists="append",
                index=False
            )
            log_info(f"Load (BBS) : {len(df_new)} nouvelle(s) entrée(s) insérée(s) (BBS_Id={bbs_id})")
        except Exception as e:
            log_info(f"❌ Erreur Load (BBS) lors de l'insertion : {e}")
            raise

    log_info("Load (BBS) : fin du chargement")


from sqlalchemy.exc import IntegrityError

def load_accidents(session_id: int, df: pd.DataFrame):
    log_info("Load (Accidents) : début de l'insertion en base")

    engine = get_sqlalchemy_engine()

    # Lecture des enregistrements existants
    existing_accidents = pd.read_sql(
        text('SELECT "Date_Acc", "Secteur_Acc", "Description_Acc" FROM public."Accident"'),
        con=engine
    )

    # Normalisation des colonnes clés
    for col in ["Secteur_Acc", "Description_Acc"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
        if col in existing_accidents.columns:
            existing_accidents[col] = existing_accidents[col].astype(str).str.strip().str.lower()

    df["Date_Acc"] = pd.to_datetime(df["Date_Acc"], errors="coerce").dt.floor('s')
    existing_accidents["Date_Acc"] = pd.to_datetime(existing_accidents["Date_Acc"], errors="coerce").dt.floor('s')

    merged = pd.merge(
        df,
        existing_accidents,
        on=["Date_Acc", "Secteur_Acc", "Description_Acc"],
        how="left",
        indicator=True
    )
    df_filtered = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df_filtered.empty:
        log_info("Load (Accidents) : aucune nouvelle entrée détectée pour insertion")
        return
    else:
        log_info(f"Load (Accidents) : {len(df_filtered)} nouvelle(s) entrée(s) à insérer")

    df_filtered["Session_Id"] = session_id

    try:
        df_filtered.to_sql(
            name="Accident",
            con=engine,
            if_exists="append",
            index=False
        )
        log_info(f"Load (Accidents) : insertion réussie de {len(df_filtered)} lignes (Session_Id={session_id})")
    except IntegrityError as e:
        # Log l'erreur sans la remonter
        log_info(f"❌ Erreur d’intégrité lors de l’insertion, doublons détectés : {e}")
        # Tu peux aussi décider de continuer sans lever d'exception
        # ou lever une exception personnalisée si tu veux signaler un warning côté front
        return


def load_impact_fibrage(session_id: int, df: pd.DataFrame):
    """
    Insère en base les lignes du DataFrame df pour l'ETL Fibrage.
    """
    log_info("Load : début insertion en base")

    engine = get_sqlalchemy_engine()

    # 1) Récupérer les Excel_row déjà insérés pour éviter les doublons
    existing_rows = pd.read_sql(
        text('SELECT "Excel_row","Impact_Id" FROM public."Impacts"'),
        con=engine
    )
    existing_rownums = set(existing_rows["Excel_row"])
    df_new = df.loc[~df["Excel_row"].isin(existing_rownums)].copy()
    if df_new.empty:
        log_info("Aucun nouvel impact à insérer.")
        return

    with engine.begin() as conn:
        count = 0
        for _, row in df_new.iterrows():
            # 2) Insert dans public."Impacts"
            impact_id = conn.execute(
                text("""
                    INSERT INTO public."Impacts"
                      ("Date_Imp","Secteur_Imp","Type_de_Perte","Excel_row")
                    VALUES (:d,:secteur,:tp,:rownum)
                    RETURNING "Impact_Id"
                """),
                {
                    "d": row["Date_Imp"],
                    "secteur": row["Secteur_Imp"],
                    "tp": row["Type_Perte"],
                    "rownum": int(row["Excel_row"])
                }
            ).scalar_one()

            # 3) Insert dans public."Impacts_Fibrage"
            conn.execute(
                text("""
                    INSERT INTO public."Impacts_Fibrage" (
                        "Impact_Id", "Poste_Imp", "Equipe_Imp",
                        "Description_Imp", "Temps_Arr_Imp",
                        "Pertes_Impact", "Nb_Filieres"
                    ) VALUES (
                        :iid, :poste, :equipe, :desc,
                        :tarr, :pertes, :nbf
                    )
                """),
                {
                    "iid": impact_id,
                    "poste": row["Poste_Imp"],
                    "equipe": row["Equipe_Imp"],
                    "desc": row["Description_Imp"],
                    "tarr": row["Temps_Arr_Imp"],
                    "pertes": row["Pertes_Impact"],
                    "nbf": row["Nb_Filieres"]
                }
            )

            # 4) Pour chaque équipement
            for col in [c for c in row.index if c.startswith("EQUIPEMENT >")]:
                val = row[col]
                if isinstance(val, str) and val.strip():
                    conn.execute(
                        text("""
                            INSERT INTO public."Impacts_Fibrage_Equipement"
                              ("Impact_Id", "Equipement_Type", "Equipement_Item")
                            VALUES (:iid, :etype, :eitem)
                        """),
                        {
                            "iid": impact_id,
                            "etype": col.split(">")[0].strip(),
                            "eitem": val.strip()
                        }
                    )

            # 5) Pour chaque AVC
            for col in [c for c in row.index if c.startswith("AVANT-CORPS >")]:
                val = row[col]
                if pd.notna(val) and str(val).strip():
                    conn.execute(
                        text("""
                            INSERT INTO public."Impacts_Fibrage_AVC"
                              ("Impact_Id", "AVC_Type", "AVC_Position")
                            VALUES (:iid, :atype, :apos)
                        """),
                        {
                            "iid": impact_id,
                            "atype": col.split(">")[1].strip(),
                            "apos": str(val).strip()
                        }
                    )

            # 6) Services
            service_codes = row["Services"].split(",") if row["Services"] else ['A_DEFINIR']
            for sc in set(service_codes):
                conn.execute(
                    text("""
                        INSERT INTO public."Impacts_Services"
                          ("Impact_Id", "Service_code")
                        VALUES (:iid, :sc)
                    """),
                    {"iid": impact_id, "sc": sc}
                )

            # 7) Liaison à la session
            conn.execute(
                text("""
                    INSERT INTO public."Sessions_Impacts"
                      ("Session_Id", "Impact_Id")
                    VALUES (:sid, :iid)
                """),
                {"sid": session_id, "iid": impact_id}
            )

            count += 1

    log_info(f"Load : {count} impact(s) fibrage inséré(s) (session_id={session_id})")

def load_impact_finissage(df: pd.DataFrame):
    """
    Insère les nouveaux impacts finissage en base :
    - Impact, Impacts_Finissage, Details, Pertes
    """
    if df.empty:
        log_info("Load : aucun nouvel impact à insérer")
        return
    engine=get_sqlalchemy_engine()
    # existing excel rows
    exist=pd.read_sql(text('SELECT "Excel_row" FROM public."Impacts"'),engine)
    df_new=df[~df['Excel_row'].isin(exist['Excel_row'])]
    if df_new.empty:
        log_info("Load : aucune nouveauté après filtrage")
        return
    with engine.begin() as conn:
        for _,r in df_new.iterrows():
            iid=conn.execute(text(
                'INSERT INTO public."Impacts" ("Date_Imp","Secteur_Imp","Type_de_Perte","Excel_row")'
                ' VALUES (:d,:s,:t,:e) RETURNING "Impact_Id"'
            ),{'d':r['Date_Imp'],'s':r['Secteur_Imp'],'t':r['Type_de_Perte'],'e':int(r['Excel_row'])}).scalar_one()
            conn.execute(text(
                'INSERT INTO public."Impacts_Finissage" ("Impact_Id","Date","Equipe_Imp","Description_Imp")'
                ' VALUES (:iid,:d,:e,:desc)'
            ),{'iid':iid,'d':r['Date_Imp'],'e':r['Equipe_Imp'],'desc':r['Description_Imp']})
            # Details
            for idx in [c for c in df_new.columns if c.startswith('Ligne_')]:
                if r[idx]==1:
                    conn.execute(text(
                        'INSERT INTO public."Impacts_Finissage_Details" ("Impact_Id","Type_Element","Nom_Element")'
                        ' VALUES (:iid,:type,:nom)'
                    ),{'iid':iid,'type':'Ligne','nom':idx})
            for col in [c for c in df_new.columns if c.startswith('Equip_')]:
                if r[col]==1:
                    nom=col.replace('Equip_','').replace('_',' ')
                    conn.execute(text(
                        'INSERT INTO public."Impacts_Finissage_Details" ("Impact_Id","Type_Element","Nom_Element")'
                        ' VALUES (:iid,:type,:nom)'
                    ),{'iid':iid,'type':'Equipement','nom':nom})
            # Pertes
            for full in [c for c in df_new.columns if c.startswith('POIDS PAR TYPE')]:
                q=r[full]
                if q>0:
                    typ=full.split('>')[-1].strip().capitalize()
                    conn.execute(text(
                        'INSERT INTO public."Impacts_Finissage_Pertes" ("Impact_Id","Type_Perte","Quantite_Perte")'
                        ' VALUES (:iid,:type,:qte)'
                    ),{'iid':iid,'type':typ,'qte':float(q)})
    log_info(f"Load : {len(df_new)} impact(s) finissage inséré(s)")
