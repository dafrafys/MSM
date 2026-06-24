# app/scripts/services/activities.py
from sqlalchemy import text
import pandas as pd
from sqlalchemy import text

def fetch_activities(engine, date_from, date_to, service_key):
    df = pd.read_sql(
        text("""
          SELECT
            a.activite_id,
            a.type_id,
            a.titre,
            a.statut,
            a.priorité,
            a.date_real::date AS date,
            a.commentaire,
            pa.personnel_id,
            CONCAT(p."Prenom",' ',p."Nom") AS nom_complet,
            p."Email"
          FROM public.activite a
          LEFT JOIN public.personnel_activite pa
            ON pa.activite_id = a.activite_id
          LEFT JOIN public."Personnel" p
            ON p."Personnel_Id" = pa.personnel_id
          WHERE a.date_real::date BETWEEN :date_from AND :date_to
            AND UPPER(a.service_key)=UPPER(:service_key)
          ORDER BY a.date_real, a.priorité, a.activite_id
        """),
        engine,
        params={"date_from": date_from, "date_to": date_to, "service_key": service_key}
    )
    activities = {}
    for row in df.itertuples():
        aid = row.activite_id
        if aid not in activities:
            activities[aid] = {
                "activite_id": aid,
                "type_id":     row.type_id,
                "titre":       row.titre,
                "date":        row.date.strftime('%Y-%m-%d'),
                "statut":      row.statut,
                "Ordre":       row.priorité,
                "commentaire": row.commentaire,
                "personnel":   []
            }
        if row.personnel_id:
            activities[aid]["personnel"].append({
                "personnel_id": row.personnel_id,
                "nom_complet":  row.nom_complet,
                "email":        row.Email,
                "commentaire":  row.commentaire
            })
    return list(activities.values())

def create_activity(engine, payload):
    sk   = payload.get("service_key", "").upper()
    prio = payload.get("priorité", 2)
    desc = payload.get("commentaire", "")

    with engine.begin() as conn:
        act_id = conn.execute(
            text("""
                INSERT INTO activite
                  (titre, type_id, date_real, priorité, statut, service_key, commentaire)
                VALUES
                  (:titre, :type_id, :date_real, :priorité, :statut, :service_key, :commentaire)
                RETURNING activite_id
            """),
            {
                **payload,
                "service_key": sk,
                "priorité": prio,
                "commentaire": desc
            }
        ).scalar()
    return act_id

def assign_or_unassign_person(engine, activite_id, personnel_id, action='assign'):
    with engine.begin() as conn:
        if action == 'assign':
            conn.execute(text("""
                INSERT INTO personnel_activite(activite_id,personnel_id)
                VALUES(:activite_id,:personnel_id)
                ON CONFLICT DO NOTHING
            """), {"activite_id": activite_id, "personnel_id": personnel_id})
        else:
            conn.execute(text("""
                DELETE FROM personnel_activite
                 WHERE activite_id = :activite_id
                   AND personnel_id = :personnel_id
            """), {"activite_id": activite_id, "personnel_id": personnel_id})


def move_activity(engine, activite_id, new_date, old_personnel_id, new_personnel_id, commentaire=None):
    with engine.begin() as conn:
        # Mise à jour de la date
        conn.execute(
            text("UPDATE activite SET date_real = :date_real WHERE activite_id = :aid"),
            {"date_real": new_date, "aid": activite_id}
        )
        # Désassignation de l'ancien
        conn.execute(
            text("DELETE FROM personnel_activite WHERE activite_id = :aid AND personnel_id = :old_pid"),
            {"aid": activite_id, "old_pid": old_personnel_id}
        )
        # Assignation du nouveau
        conn.execute(
            text("""
                INSERT INTO personnel_activite (activite_id, personnel_id)
                VALUES (:aid,:new_pid) ON CONFLICT DO NOTHING
            """),
            {"aid": activite_id, "new_pid": new_personnel_id}
        )
def reorder_activities(engine, ordered_activities):
    with engine.begin() as conn:
        for act in ordered_activities:
            conn.execute(
                text("UPDATE activite SET priorité = :prio WHERE activite_id = :aid"),
                {"prio": act['priorité'], "aid": act['activite_id']}
            )


def delete_activity(engine, activite_id):
    with engine.begin() as conn:
        # Supprimer les assignations puis l'activité
        conn.execute(text("DELETE FROM personnel_activite WHERE activite_id = :aid"), {"aid": activite_id})
        conn.execute(text("DELETE FROM activite WHERE activite_id = :aid"), {"aid": activite_id})

def update_activity_status(engine, activite_id, new_status):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE activite SET statut = :statut WHERE activite_id = :aid"),
            {"statut": new_status, "aid": activite_id}
        )

def update_activity_fields(engine, activite_id, data):
    updates = []
    params = {"aid": activite_id}

    if "titre" in data and data["titre"] is not None:
        updates.append("titre = :titre")
        params["titre"] = data["titre"]

    if "commentaire" in data and data["commentaire"] is not None:
        updates.append("commentaire = :commentaire")
        params["commentaire"] = data["commentaire"]

    if not updates:
        raise ValueError("Aucun champ à mettre à jour")

    sql = f"UPDATE activite SET {', '.join(updates)} WHERE activite_id = :aid"

    with engine.begin() as conn:
        conn.execute(text(sql), params)
