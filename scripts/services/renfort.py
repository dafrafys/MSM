# app/scripts/services/renfort.py

import uuid
from sqlalchemy import text
from datetime import datetime, time

def add_renfort(engine, nom_complet, date_debut, date_fin, service_code, equipe):
    personnel_id = str(uuid.uuid4())[:20]  # max 20 caractères
    role = "renfort"
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO "Personnel"
            ("Personnel_Id", "Nom", "Prenom", "Role", "Date_Debut_Renfort", "Date_Fin_Renfort", "is_renfort", "Service_code", "Equipe")
            VALUES (:pid, :nom, '', :role, :date_debut, :date_fin, true, :service_code, :equipe)
        """), {
            "pid": personnel_id,
            "nom": nom_complet,
            "role": role,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "service_code": service_code.upper(),
            "equipe": equipe
        })
    return personnel_id

def add_or_reactivate_renfort(engine, nom_complet, date_debut, date_fin, service_code, equipe):
    with engine.begin() as conn:
        # Chercher renfort inactif existant
        sql_select = text("""
            SELECT "Personnel_Id" FROM public."Personnel"
            WHERE ("Nom" || ' ' || "Prenom") = :nom_complet
              AND "Service_code" = :service_code
              AND "Equipe" = :equipe
              AND is_renfort = true AND is_active = false
            LIMIT 1
        """)
        result = conn.execute(sql_select, {
            "nom_complet": nom_complet,
            "service_code": service_code,
            "equipe": equipe
        })
        row = result.first()

        if row:
            # Réactiver renfort existant
            personnel_id = row["Personnel_Id"]
            sql_update = text("""
                UPDATE public."Personnel"
                SET is_active = true,
                    "Date_Debut_Renfort" = :date_debut,
                    "Date_Fin_Renfort" = :date_fin,
                    "Equipe" = :equipe
                WHERE "Personnel_Id" = :pid
            """)
            conn.execute(sql_update, {
                "date_debut": date_debut,
                "date_fin": date_fin,
                "equipe": equipe,
                "pid": personnel_id
            })
        else:
            # Insérer nouveau renfort
            personnel_id = str(uuid.uuid4())[:20]
            sql_insert = text("""
                INSERT INTO public."Personnel"
                ("Personnel_Id", "Nom", "Prenom", "Role", "Date_Debut_Renfort", "Date_Fin_Renfort",
                 is_renfort, is_active, "Service_code", "Equipe")
                VALUES (:pid, :nom, '', 'renfort', :date_debut, :date_fin, true, true, :service_code, :equipe)
            """)
            conn.execute(sql_insert, {
                "pid": personnel_id,
                "nom": nom_complet,
                "date_debut": date_debut,
                "date_fin": date_fin,
                "service_code": service_code,
                "equipe": equipe
            })
    return personnel_id

def fetch_renforts(engine, date_from, date_to, service_code):
    sql = text("""
        SELECT
            "Personnel_Id",
            "Nom" || ' ' || "Prenom" AS nom_complet,
            "Date_Debut_Renfort",
            "Date_Fin_Renfort",
            is_active,
            is_renfort,
            "Equipe",
            "Service_code"
        FROM public."Personnel"
        WHERE is_renfort = true
          AND is_active = true
          AND "Date_Debut_Renfort" <= :date_to
          AND "Date_Fin_Renfort" >= :date_from
          AND UPPER("Service_code") = UPPER(:service_code)
        ORDER BY "Nom", "Prenom"
    """)
    with engine.connect() as conn:
        result = conn.execute(sql, {"date_from": date_from, "date_to": date_to, "service_code": service_code})
        renforts = [dict(row) for row in result.mappings()]
    return renforts

# Fonction métier indépendante (retourne une liste de dicts)
def get_all_renforts(engine):
    sql = text("""
        SELECT
            "Personnel_Id",
            "Nom" || ' ' || "Prenom" AS nom_complet,
            "Date_Debut_Renfort",
            "Date_Fin_Renfort",
            is_active,
            is_renfort,
            "Equipe"
        FROM public."Personnel"
        WHERE is_renfort = true
        ORDER BY "Nom", "Prenom"
    """)
    with engine.connect() as conn:
        result = conn.execute(sql)
        renforts = [dict(row) for row in result.mappings()]
    return renforts


def set_renfort_inactive(engine, personnel_id):
    sql = text("""
        UPDATE public."Personnel"
        SET is_active = false,
            "Date_Debut_Renfort" = NULL,
            "Date_Fin_Renfort" = NULL
        WHERE "Personnel_Id" = :personnel_id
          AND is_renfort = true
    """)
    with engine.connect() as conn:
        result = conn.execute(sql, {"personnel_id": personnel_id})
        conn.commit()
    return result.rowcount

def prolonger_renfort(engine, personnel_id, new_date_fin_str):
    try:
        new_date_fin = datetime.strptime(new_date_fin_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Format date_fin invalide, attendu AAAA-MM-JJ")

    with engine.connect() as conn:
        current_fin = conn.execute(text("""
            SELECT "Date_Fin_Renfort"
            FROM public."Personnel"
            WHERE "Personnel_Id" = :pid AND is_renfort = true
        """), {"pid": personnel_id}).scalar()

        if current_fin is None:
            return None  # renfort non trouvé

        if new_date_fin <= current_fin:
            return jsonify({
                "description": "Nouvelle date de fin doit être postérieure à la date actuelle",
                "current_date_fin": current_fin.strftime("%Y-%m-%d")
            }), 400

        conn.execute(text("""
            UPDATE public."Personnel"
            SET "Date_Fin_Renfort" = :new_date_fin
            WHERE "Personnel_Id" = :pid AND is_renfort = true
        """), {"new_date_fin": new_date_fin, "pid": personnel_id})
        conn.commit()
    return True
