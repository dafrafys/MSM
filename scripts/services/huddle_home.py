# app/services/huddle_home.py
# Toute la logique métier de la page d'accueil
from flask import current_app, jsonify
from sqlalchemy import text
import calendar
from datetime import date, timedelta
from collections import defaultdict
import pandas as pd
from collections import defaultdict
import json

import logging

logger = logging.getLogger(__name__)

def get_impacts(engine, sid, *, year=None, month=None, start_date=None, end_date=None):
    # Construction de la clause WHERE
    if start_date and end_date:
        where_clause = 'i."Date_Imp" BETWEEN :start_date AND :end_date'
        params = {"sid": sid, "start_date": start_date, "end_date": end_date}
    elif year and month:
        where_clause = ('EXTRACT(YEAR FROM i."Date_Imp") = :year AND '
                        'EXTRACT(MONTH FROM i."Date_Imp") = :month')
        params = {"sid": sid, "year": year, "month": month}
    else:
        raise ValueError("Il faut soit year/month, soit start_date/end_date")

    # Requête pour fibrage
    sql_fibrage = f"""
    WITH details AS (
        SELECT
            f."Impact_Id", f."Poste_Imp", f."Equipe_Imp",
            f."Description_Imp", f."Temps_Arr_Imp", f."Pertes_Impact",
            STRING_AGG(DISTINCT fe."Equipement_Item", ', ') AS equipement,
            STRING_AGG(DISTINCT av."AVC_Position", ', ') AS ligne
        FROM public."Impacts_Fibrage" f
        LEFT JOIN public."Impacts_Fibrage_Equipement" fe
            ON fe."Impact_Id" = f."Impact_Id"
        LEFT JOIN public."Impacts_Fibrage_AVC" av
            ON av."Impact_Id" = f."Impact_Id"
        GROUP BY f."Impact_Id", f."Poste_Imp", f."Equipe_Imp",
                 f."Description_Imp", f."Temps_Arr_Imp", f."Pertes_Impact"
    )
    SELECT
        i."Impact_Id", i."Date_Imp" AS date,
        i."Plan_Uploaded" AS plan_uploaded,
        d."Poste_Imp" AS poste,
        i."Type_de_Perte" AS type_perte,
        i."Secteur_Imp" AS secteur,
        d.ligne AS ligne,
        d.equipement AS equipement,
        d."Description_Imp" AS description,
        d."Temps_Arr_Imp" AS temps_arret,
        d."Pertes_Impact" AS pertes
    FROM public."Impacts" i
    JOIN details d ON d."Impact_Id" = i."Impact_Id"
    WHERE {where_clause}
    ORDER BY i."Date_Imp" DESC, i."Impact_Id" DESC
    """

    # Requête pour finissage avec agrégation JSON des pertes
    sql_finissage = f"""
    WITH pertes AS (
        SELECT
            "Impact_Id",
            json_agg(json_build_object('type', "Type_Perte", 'poids', "Quantite_Perte")) AS pertes
        FROM public."Impacts_Finissage_Pertes"
        GROUP BY "Impact_Id"
    )
    SELECT
        i."Impact_Id",
        i."Date_Imp" AS date,
        i."Plan_Uploaded" AS plan_uploaded,
        f."Equipe_Imp" AS equipe,
        i."Type_de_Perte" AS type_perte,
        i."Secteur_Imp" AS secteur,
        f."Description_Imp" AS description,
        d.lignes AS ligne,
        d.equipements AS equipement,
        pertes.pertes AS pertes
    FROM public."Impacts" i
    JOIN public."Impacts_Finissage" f ON f."Impact_Id" = i."Impact_Id"
    LEFT JOIN (
        SELECT
            "Impact_Id",
            STRING_AGG(CASE WHEN "Type_Element" = 'Ligne' THEN "Nom_Element" END, ', ') AS lignes,
            STRING_AGG(CASE WHEN "Type_Element" = 'Equipement' THEN "Nom_Element" END, ', ') AS equipements
        FROM public."Impacts_Finissage_Details"
        GROUP BY "Impact_Id"
    ) d ON d."Impact_Id" = i."Impact_Id"
    LEFT JOIN pertes ON pertes."Impact_Id" = i."Impact_Id"
    WHERE {where_clause}
    ORDER BY i."Date_Imp" DESC, i."Impact_Id" DESC
    """

    # Exécution des requêtes
    fibrage_df = pd.read_sql(text(sql_fibrage), engine, params=params)
    finissage_df = pd.read_sql(text(sql_finissage), engine, params=params)
    logger.debug(f"Fibrage sample:\n{fibrage_df.head().to_dict(orient='records')}")
    logger.debug(f"Finissage sample raw:\n{finissage_df.head().to_dict(orient='records')}")

    # Transformation en dict et nettoyage pertes JSON
    finissage_records = finissage_df.to_dict(orient='records')
    for imp in finissage_records:
        if isinstance(imp.get('pertes'), str):
            imp['pertes'] = json.loads(imp['pertes'])
        elif imp.get('pertes') is None:
            imp['pertes'] = []
        imp['impact_id'] = imp['Impact_Id']
        imp['plan_uploaded'] = imp.get('plan_uploaded', False)

    logger.debug(f"Finissage post-processed sample:\n{finissage_records[:3]}")

    # Post-traitement fibrage (inchangé)
    fibrage_records = fibrage_df.to_dict(orient='records')
    for imp in fibrage_records:
        imp["impact_id"] = imp["Impact_Id"]
        imp["plan_uploaded"] = imp.get("plan_uploaded", False)

    return fibrage_records, finissage_records

def get_impact_details(engine, impact_id):
    try:
        # Vérifie si l’impact est fibrage
        is_fibrage = pd.read_sql(
            text("""SELECT COUNT(*) AS count FROM public."Impacts_Fibrage" WHERE "Impact_Id" = :id"""),
            engine, params={"id": impact_id}
        ).iloc[0]["count"] > 0

        if is_fibrage:
            query = text("""
                WITH details AS (
                    SELECT
                        f."Impact_Id", f."Poste_Imp", f."Description_Imp",
                        f."Temps_Arr_Imp", f."Pertes_Impact",
                        STRING_AGG(fe."Equipement_Item", ', ') AS equipement,
                        STRING_AGG(av."AVC_Position", ', ') AS ligne
                    FROM public."Impacts_Fibrage" f
                    LEFT JOIN public."Impacts_Fibrage_Equipement" fe ON fe."Impact_Id" = f."Impact_Id"
                    LEFT JOIN public."Impacts_Fibrage_AVC" av ON av."Impact_Id" = f."Impact_Id"
                    WHERE f."Impact_Id" = :impact_id
                    GROUP BY f."Impact_Id", f."Poste_Imp", f."Description_Imp",
                             f."Temps_Arr_Imp", f."Pertes_Impact"
                )
                SELECT
                    i."Impact_Id"      AS impact_id,
                    i."Date_Imp"       AS date,
                    d.equipement       AS equipement,
                    d.ligne            AS ligne,
                    i."Type_de_Perte"  AS type_perte,
                    i."Secteur_Imp"    AS secteur,
                    d."Poste_Imp"      AS poste,
                    d."Description_Imp"AS description,
                    d."Temps_Arr_Imp"  AS temps_arret,
                    d."Pertes_Impact"  AS pertes
                FROM public."Impacts" i
                JOIN details d ON d."Impact_Id" = i."Impact_Id"
                WHERE i."Impact_Id" = :impact_id
            """)
        else:
            query = text("""
                WITH pertes AS (
                    SELECT "Impact_Id",
                           json_agg(json_build_object('type', "Type_Perte", 'poids', "Quantite_Perte")) AS pertes
                    FROM public."Impacts_Finissage_Pertes"
                    GROUP BY "Impact_Id"
                )
                SELECT
                    i."Impact_Id"      AS impact_id,
                    i."Date_Imp"       AS date,
                    NULL               AS equipement,
                    NULL               AS ligne,
                    i."Type_de_Perte"  AS type_perte,
                    i."Secteur_Imp"    AS secteur,
                    f."Poste_Imp"      AS poste,
                    f."Description_Imp"AS description,
                    NULL               AS temps_arret,
                    pertes.pertes      AS pertes
                FROM public."Impacts" i
                JOIN public."Impacts_Finissage" f ON f."Impact_Id" = i."Impact_Id"
                LEFT JOIN pertes ON pertes."Impact_Id" = i."Impact_Id"
                WHERE i."Impact_Id" = :impact_id
            """)

        df = pd.read_sql(query, engine, params={"impact_id": impact_id})

        if df.empty:
            current_app.logger.warning(f"Impact non trouvé pour ID {impact_id}")
            return None

        impact = df.iloc[0].to_dict()

        # Formatage des dates
        if isinstance(impact.get("date"), pd.Timestamp):
            impact["date"] = impact["date"].strftime("%Y-%m-%d")

        if isinstance(impact.get("temps_arret"), pd.Timedelta):
            impact["temps_arret"] = int(impact["temps_arret"].total_seconds())

        # Conversion des pertes JSON en liste Python
        if isinstance(impact.get("pertes"), str):
            impact["pertes"] = json.loads(impact["pertes"])
        elif not impact.get("pertes"):
            impact["pertes"] = []

        return impact

    except Exception as e:
        current_app.logger.exception(f"Erreur dans get_impact_details pour ID {impact_id}: {e}")
        return None

def insert_carte_stop(engine, session_id, personnel_id, date_realisation):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO public."carte_stop" ("Session_Id", "Personnel_Id", "date_realisation")
            VALUES (:session_id, :personnel_id, :date_realisation)
        """), {
            "session_id": session_id,
            "personnel_id": personnel_id,
            "date_realisation": date_realisation,
        })

def upsert_suivi_hebdo_cs(engine, service_code, semaine_annee, nombre_OT):
    with engine.begin() as conn:
        existing = conn.execute(text("""
            SELECT id FROM public.suivi_hebdo_cs
            WHERE service_code = :service_code AND semaine_annee = :semaine_annee
        """), {"service_code": service_code, "semaine_annee": semaine_annee}).fetchone()

        if existing:
            conn.execute(text("""
                UPDATE public.suivi_hebdo_cs
                SET nombre_OT = :nombre_OT, date_saisie = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"nombre_OT": nombre_OT, "id": existing.id})
        else:
            conn.execute(text("""
                INSERT INTO public.suivi_hebdo_cs (service_code, semaine_annee, nombre_OT)
                VALUES (:service_code, :semaine_annee, :nombre_OT)
            """), {"service_code": service_code, "semaine_annee": semaine_annee, "nombre_OT": nombre_OT})

def get_ratio_cartes_stop_hebdo(engine, semaine_annee):
    """
    Retourne la liste des ratios hebdomadaires cartes stop / opérations par service
    pour la semaine donnée (format 'YYYY-Www' ISO).
    """
    sql = """
    WITH cartes_stop_semaine AS (
        SELECT
          p."Service_code",
          COUNT(cs."carte_id") AS nb_cartes_semaine
        FROM public."carte_stop" cs
        JOIN public."Personnel" p ON cs."Personnel_Id" = p."Personnel_Id"
        WHERE TO_CHAR(cs."date_realisation", 'IYYY-IW') = :semaine_annee
        GROUP BY p."Service_code"
    ),
    ot_necessaire_semaine AS (
        SELECT
          service_code,
          "nombre_OT" AS ot_necessaire
        FROM public."suivi_hebdo_cs"
        WHERE semaine_annee = :semaine_annee
    )
    SELECT
      c."Service_code",
      COALESCE(o.ot_necessaire, 0) AS ot_necessaire,
      COALESCE(c.nb_cartes_semaine, 0) AS cartes_stop_semaine
    FROM cartes_stop_semaine c
    LEFT JOIN ot_necessaire_semaine o ON c."Service_code" = o.service_code;
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql), {"semaine_annee": semaine_annee})
        ratios = [dict(row._mapping) for row in result]

    for row in ratios:
        cartes_stop_semaine = row.get("cartes_stop_semaine", 0)
        ot_necessaire = row.get("ot_necessaire", 0)
        row["ratio_hebdo"] = (cartes_stop_semaine / ot_necessaire) * 100 if ot_necessaire > 0 else None
        row["pourcentage_sur_mois"] = (cartes_stop_semaine / total_cartes_mois) * 100 if total_cartes_mois > 0 else None

    return ratios

def get_huddle_home_context(engine, sid=None, session_date_str=None, config=None, year=None, month=None):
    """
    Calcule tous les contextes de la page d'accueil du huddle :
    progression BBS, stats, accidents, impacts, carte stop,etc.
    Retourne un dict prêt à injecter dans render_template().
    """
    today = date.today()
    year, month = today.year, today.month
    semaine_annee = today.strftime('%G-W%V')
    session_date_display = None
    no_session_found = False

    # Si year ou month ne sont pas fournis, prendre la date actuelle
    if year is None or month is None:
        today = date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month

    # 1) Chercher la session courante ou par date
    session_date_display = None
    no_session_found = False

    if session_date_str:
        session_date = pd.to_datetime(session_date_str).date()
        result = pd.read_sql("""
            SELECT "Session_Id", date_session
            FROM public."Huddle_Session"
            WHERE date_session::date = %(session_date)s
            ORDER BY "Session_Id" DESC
            LIMIT 1
        """, engine, params={"session_date": session_date})
        if not result.empty:
            sid = result.iloc[0]["Session_Id"]
            session_date_display = result.iloc[0]["date_session"]
            no_session_found = False
        else:
            sid = None
            session_date_display = session_date
            no_session_found = True

    # Si pas de session trouvée par date et sid est None, prendre la dernière session existante
    if not session_date_str or sid is None:
        result = pd.read_sql("""
            SELECT "Session_Id", date_session
            FROM public."Huddle_Session"
            ORDER BY date_session DESC
            LIMIT 1
        """, engine)
        if not result.empty:
            sid = result.iloc[0]["Session_Id"]
            session_date_display = result.iloc[0]["date_session"]
            no_session_found = False

    # 2) Requête BBS
    with engine.connect() as conn:
        # Récupérer tous les personnels éligibles + nombre de BBS ce mois-ci
        query = text("""
            SELECT
                p."Personnel_Id",
                p."Nom",
                p."Prenom",
                COUNT(bs."BBS_Stat_Id") AS nombre_bbs
            FROM public."Personnel" p
            LEFT JOIN public."BBS_Stat" bs
                ON p."Personnel_Id" = bs."Personnel_Id"
                AND EXTRACT(YEAR FROM bs."Date_BBS") = :year
                AND EXTRACT(MONTH FROM bs."Date_BBS") = :month
            WHERE LOWER(p."Role") NOT IN ('membre', 'admin', 'renfort')
               OR (p."Nom" = 'GUILLET' AND p."Prenom" = 'Christian')
               OR (p."Nom" = 'SCHUSTER' AND p."Prenom" = 'Alexis')
            GROUP BY p."Personnel_Id", p."Nom", p."Prenom"
            ORDER BY nombre_bbs DESC NULLS LAST
        """)
        result = conn.execute(query, {"year": year, "month": month})
        personnels = [dict(row._mapping) for row in result]

    nb_personnes = len(personnels)
    bbs_count = sum(p['nombre_bbs'] for p in personnels)

    objectif_total = nb_personnes * (config.OBJECTIF_PAR_PERSONNE if config else 2)
    progression_bbs = round((bbs_count / objectif_total) * 100, 2) if objectif_total else 0

    days_in_month = calendar.monthrange(year, month)[1]
    expected_pct = round((today.day / days_in_month) * 100, 2)

    if progression_bbs >= expected_pct:
        bbs_status = "good"
    elif progression_bbs >= expected_pct * 0.75:
        bbs_status = "warning"
    else:
        bbs_status = "critical"

    # Séparer ceux qui ont fait des BBS et ceux qui ne l'ont pas fait
    bbs_individus = [p for p in personnels if p['nombre_bbs'] > 0]
    personnels_sans_bbs = [p for p in personnels if p['nombre_bbs'] == 0]

    # 7) Accidents récents
    accidents_query = '''
        SELECT "Type_Acc", "Classe_Acc", "Date_Acc" AS date,
               "Service_Acc", "Secteur_Acc" AS zone,
               "Description_Acc" AS description, "Accident_Id"
        FROM public."Accident"
        ORDER BY "Accident_Id" DESC
    '''
    df_acc = pd.read_sql(accidents_query, engine)
    records = df_acc.to_dict(orient='records')
    for acc in records:
        raw_date = acc.get("date")
        acc["date_str"] = raw_date.strftime("%d/%m/%Y") if raw_date and pd.notna(raw_date) else None
    accidents = records

    # 8) Jours sans accident + dernier accident
    days_query = text('''
        SELECT
            MAX("Date_Acc") AS last_accident_date,
            (CURRENT_DATE - MAX("Date_Acc")) AS days_without_accident
        FROM public."Accident"
        WHERE "Service_Acc" = 'Maintenance'
          AND "Date_Acc" <= CURRENT_DATE
    ''')
    with engine.connect() as conn:
        last_date, delta = conn.execute(days_query).fetchone()
    last_accident_date = last_date if last_date else None
    days_without_accident = delta.days if delta is not None else 0

    # 9) Croix de sécurité
    nb_days = days_in_month
    cross_query = text('''
        SELECT "Date_Acc", "Type_Acc"
        FROM public."Accident"
        WHERE "Service_Acc" = 'Maintenance'
          AND EXTRACT(YEAR FROM "Date_Acc") = :year
          AND EXTRACT(MONTH FROM "Date_Acc") = :month
    ''')
    with engine.connect() as conn:
        rows = conn.execute(cross_query, {"year": year, "month": month}).fetchall()
    priority_map = {"AA": 3, "SA": 2, "SS": 1}
    day_accidents = defaultdict(lambda: ("", 0))
    for acc_date, type_acc in rows:
        d = acc_date.day
        p = priority_map.get(type_acc, 0)
        _, current_p = day_accidents[d]
        if p > current_p:
            day_accidents[d] = (type_acc, p)
    day_status = {}
    for d in range(1, nb_days + 1):
        if d in day_accidents:
            best_type, _ = day_accidents[d]
            day_status[d] = best_type
        else:
            if year == today.year and month == today.month and d < today.day:
                day_status[d] = "safe"
            else:
                day_status[d] = "empty"

    # 9+10) Récupération des impacts fibrage et finissage en un seul appel
    impacts_fibrage, impacts_finissage = get_impacts(
        engine, sid,
        year=year, month=month
    )

    # Liste des types d'analyse possibles
    types_analyse = ["Non couverte", "Détaillée", "Rapide", "autres"]

    # Liste des statuts
    statuts = ["En cours", "Clôturé", "À suivre"]

    # Liste des Personnel
    with engine.connect() as conn:
        personnels = pd.read_sql("""
            SELECT "Personnel_Id", CONCAT("Prenom", ' ', "Nom") AS nom_complet
            FROM public."Personnel"
            ORDER BY "Nom", "Prenom"
        """, conn).to_dict(orient="records")

        cartes_stop_count = conn.execute(text("""
            SELECT COUNT(*)
            FROM public."carte_stop"
            WHERE EXTRACT(YEAR FROM "date_realisation") = :year
              AND EXTRACT(MONTH FROM "date_realisation") = :month
        """), {"year": year, "month": month}).scalar()

        cartes_stop_par_service = conn.execute(text("""
            SELECT
              p."Service_code",
              COUNT(cs."carte_id") FILTER (
                WHERE EXTRACT(YEAR FROM cs."date_realisation") = :year
                  AND EXTRACT(MONTH FROM cs."date_realisation") = :month
              ) AS nb_cartes_mois,
              COUNT(cs."carte_id") FILTER (
                WHERE cs."date_realisation" = CURRENT_DATE
              ) AS nb_cartes_aujourdhui
            FROM public."carte_stop" cs
            JOIN public."Personnel" p ON cs."Personnel_Id" = p."Personnel_Id"
            GROUP BY p."Service_code"
            ORDER BY nb_cartes_mois DESC
        """), {"year": year, "month": month}).mappings().all()

        selected_month_year = f"{year:04d}-{month:02d}"

    # Appel du ratio cartes stop hebdo
    ratios_cartes_stop = get_ratio_cartes_stop_hebdo(engine, semaine_annee)



    return {
        "session_id": sid,
        "session_date_display": session_date_display,
        "no_session_found": no_session_found,
        "progression_bbs": progression_bbs,
        "expected_pct": expected_pct,
        "bbs_status": bbs_status,
        "bbs_individus": bbs_individus,
        "personnels_sans_bbs": personnels_sans_bbs,
        "accidents": accidents,
        "last_accident_date": last_accident_date,
        "days_without_accident": days_without_accident,
        "day_status": day_status,
        "year": year,
        "month": month,
        "impacts_fibrage": impacts_fibrage,
        "impacts_finissage": impacts_finissage,
        "personnels": personnels,
        "types_analyse": types_analyse,
        "cartes_stop_count": cartes_stop_count,
        "statuts": statuts,
        "cartes_stop_par_service": cartes_stop_par_service,
        "ratios_cartes_stop": ratios_cartes_stop,
        "selected_month_year": selected_month_year,
    }
