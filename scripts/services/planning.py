# app/scripts/services/planning.py

from datetime import date, timedelta
import calendar

import pandas as pd
from sqlalchemy import text

def get_planning_data(engine, service_key, view='week', week_offset=0, month_offset=0):
    # 1. Récupère les labels (le blueprint passera le dict déjà prêt)
    # 2. Récupère le personnel
    personnel = pd.read_sql(
        text("""
        SELECT p."Personnel_Id",
                CONCAT(p."Prenom",' ',p."Nom") AS nom_complet,
                p."Equipe",
                p."is_renfort",
                p.is_active
         FROM public."Personnel" p
         WHERE
            (
                p."is_renfort" = false
                AND UPPER(p."Service_code") LIKE '%' || UPPER(:service_key)
            )
            OR
            (
                p."is_renfort" = true
                AND CURRENT_DATE BETWEEN p."Date_Debut_Renfort" AND p."Date_Fin_Renfort"
                AND UPPER(p."Service_code") = UPPER(:service_key)
                AND (p.is_active IS NULL OR p.is_active = true)
            )
         ORDER BY p."Nom", p."Prenom"
         """),
         engine,
         params={"service_key": service_key}
    ).to_dict(orient="records")

    type_catalogue = pd.read_sql(
        text("SELECT type_id, libelle FROM type_activite ORDER BY libelle"),
        engine
    ).to_dict(orient="records")
    color_palette = ["#e74c3c", "#27ae60", "#2980b9", "#f39c12", "#8e44ad", "#b4edc2", "#d35400"]
    for i, t in enumerate(type_catalogue):
        t["color"] = color_palette[i % len(color_palette)]

    today = date.today()
    if view == 'month':
        target_date = today + relativedelta(months=month_offset)
        year, month = target_date.year, target_date.month
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(year, month)
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        date_from = first_day.strftime('%Y-%m-%d')
        date_to   = last_day.strftime('%Y-%m-%d')
        week_days_display = []
        week_days_full = []
        week_number = None
        start_week = None
        month_label = None
    else:
        week_offset = int(week_offset)
        start_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        week_number = start_week.isocalendar()[1]
        month_label = start_week.strftime("%B")
        week_days_full = [(start_week + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        week_days_display = [(start_week + timedelta(days=i)).strftime('%d') for i in range(7)]
        date_from = week_days_full[0]
        date_to   = week_days_full[-1]
        year, month = start_week.year, start_week.month
        cal = calendar.Calendar(firstweekday=0)
        month_matrix = cal.monthdayscalendar(year, month)

    # Activités
    df = pd.read_sql(
        text("""
          SELECT
            a.activite_id,
            a.type_id,
            a.titre,
            a.statut,
            a.date_real::date AS date,
            pa.personnel_id,
            CONCAT(p."Prenom",' ',p."Nom") AS nom_complet
          FROM public.activite a
          LEFT JOIN public.personnel_activite pa
            ON pa.activite_id = a.activite_id
          LEFT JOIN public."Personnel" p
            ON p."Personnel_Id" = pa.personnel_id
          WHERE a.date_real::date BETWEEN :date_from AND :date_to
            AND UPPER(a.service_key) = UPPER(:service_key)
          ORDER BY a.activite_id
        """),
        engine,
        params={
            "date_from": date_from,
            "date_to": date_to,
            "service_key": service_key
        }
    )

    activities = {}
    for row in df.itertuples():
        aid = row.activite_id
        if aid not in activities:
            activities[aid] = {
                "activite_id": aid,
                "titre":       row.titre,
                "type_id":     row.type_id,
                "date":        row.date.strftime('%Y-%m-%d'),
                "statut":      row.statut,
                "personnel":   []
            }
        if row.personnel_id:
            activities[aid]["personnel"].append({
                "personnel_id": row.personnel_id,
                "nom_complet":  row.nom_complet
            })

    res = list(activities.values())

    # Récupérer les infos journalières pour le service et la période
    infos_df = pd.read_sql(
        text("""
            SELECT info_date, info_text
            FROM public.service_info
            WHERE service_code = :service_key
              AND info_date BETWEEN :date_from AND :date_to
        """),
        engine,
        params={"service_key": service_key, "date_from": date_from, "date_to": date_to}
    )

    # Convertir en dict date -> texte
    infos_df['info_date'] = pd.to_datetime(infos_df['info_date'], errors='coerce')
    infos_df['info_date'] = infos_df['info_date'].dt.strftime('%Y-%m-%d')
    infos = infos_df.set_index('info_date')['info_text'].to_dict()

    return {
        "personnel": personnel,
        "type_catalogue": type_catalogue,
        "view_mode": view,
        "month_matrix": month_matrix,
        "month_year": (year, month),
        "week_number": week_number,
        "start_week": start_week,
        "month_label": month_label,
        "week_days": week_days_display,
        "week_days_full": week_days_full,
        "activities": res,
        "service_infos": infos,
    }
