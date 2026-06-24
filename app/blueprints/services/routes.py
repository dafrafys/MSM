# app/blueprints/services/routes.py
from flask import request, jsonify, current_app, Blueprint, render_template, abort
from . import bp
from scripts.services.supervision import fetch_supervision
from scripts.services.activities import fetch_activities, assign_or_unassign_person, update_activity_status
from app.extensions import get_raw_engine
from scripts.services.activities import update_activity_fields, reorder_activities
from scripts.services.activities import create_activity as create_activity_service
from scripts.services.activities import move_activity as svc_move_activity
from scripts.services.activities import delete_activity as svc_delete_activity
from scripts.services.renfort import add_renfort as service_add_renfort, add_or_reactivate_renfort, prolonger_renfort, fetch_renforts, set_renfort_inactive, get_all_renforts
from scripts.services.planning_utils import shift_for
from scripts.services.planning import get_planning_data
from scripts.services.sharepoint import fetch_excel_data
from sqlalchemy import text
from datetime import datetime




import locale

for loc in ("fr_FR.UTF-8", "fr_FR.utf8", "fr_FR", ""):
    try:
        locale.setlocale(locale.LC_TIME, loc)
        break
    except locale.Error:
        continue

# ─── API : récupération des Rapport ────────────────────────────────────────────
@bp.get('/api/sharepoint')
def api_sharepoint():
    current_app.logger.debug("Appel API : récupération du fichier Excel SharePoint")
    try:
        data = fetch_excel_data()
        current_app.logger.info(f"Renvoi de {len(data)} lignes Excel")
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Erreur SharePoint Excel : {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ─── API : récupération des alarmes ────────────────────────────────────────────
@bp.get('/api/supervision')
def api_supervision():
    current_app.logger.debug("🔔 api_supervision called")
    try:
        results = fetch_supervision()
        return jsonify(results), 200
    except Exception as e:
        current_app.logger.error(f"Erreur récupération alarmes : %s", e)
        return jsonify({"status":"error","message": str(e)}), 500

# ─── API : récupération des activités ────────────────────────────────────────────
@bp.get('/api/activities')
def api_get_activities():
    date_from = request.args.get('from')
    date_to   = request.args.get('to')
    service   = request.args.get('service_key')
    engine = get_raw_engine()
    activities = fetch_activities(engine, date_from, date_to, service)
    current_app.logger.debug(f"[services] api_get_activities returning {len(activities)} activities")
    return jsonify(activities)

# ─── API : Création des activités ───────────────────────────────────────────
@bp.post('/api/activities')
def create_activity():
    d = request.get_json() or {}
    engine = get_raw_engine()
    act_id = create_activity_service(engine, d)
    current_app.logger.debug(f"[services] create_activity inserted id={act_id}")
    return jsonify(activite_id=act_id), 201

# ─── API : récupération des infos journalières ────────────────────────────────
@bp.get('/api/service_info')
def api_get_service_info():
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    service_key = request.args.get('service_key')
    if not date_from or not date_to or not service_key:
        abort(400, "Paramètres manquants : from, to, service_key requis")
    service_key = service_key.upper()

    current_app.logger.info(f"API GET service_info called with from={date_from}, to={date_to}, service_key={service_key}")

    engine = get_raw_engine()
    sql = text("""
        SELECT info_date, service_code, info_text
        FROM public.service_info
        WHERE service_code = :service_key
          AND info_date BETWEEN :date_from AND :date_to
        ORDER BY info_date
    """)
    with engine.connect() as conn:
        result = conn.execute(sql, {"service_key": service_key, "date_from": date_from, "date_to": date_to})
        data = [dict(row._mapping) for row in result]

    current_app.logger.info(f"Returned {len(data)} entries for service_info")
    return jsonify(data)



# ─── API : création ou mise à jour d'une info journalière ────────────────────
@bp.post('/api/service_info')
def api_post_service_info():
    d = request.get_json() or {}
    info_date = d.get('info_date')
    service_code = d.get('service_code')
    info_text = d.get('info_text', '').strip()
    if not info_date or not service_code or not info_text:
        abort(400, "Champs manquants : info_date, service_code et info_text requis")
    service_code = service_code.upper()

    engine = get_raw_engine()
    sql_upsert = text("""
        INSERT INTO public.service_info (info_date, service_code, info_text)
        VALUES (:info_date, :service_code, :info_text)
        ON CONFLICT (info_date, service_code)
        DO UPDATE SET info_text = EXCLUDED.info_text
    """)
    with engine.connect() as conn:
        conn.execute(
            sql_upsert,
            {"info_date": info_date, "service_code": service_code, "info_text": info_text}
        )
        conn.commit()
    return jsonify(status='ok'), 201


@bp.delete('/api/service_info/<string:info_date>/<string:service_code>')
def delete_service_info(info_date, service_code):
    engine = get_raw_engine()
    sql = text("""
        DELETE FROM public.service_info
        WHERE info_date = :info_date AND service_code = :service_code
    """)
    service_code = service_code.upper()  # forcer la casse si besoin

    with engine.connect() as conn:
        result = conn.execute(sql, {"info_date": info_date, "service_code": service_code})
        conn.commit()

    if result.rowcount == 0:
        return jsonify({"error": "Info non trouvée"}), 404
    return jsonify(status='deleted'), 200

# ─── API : Affectation  ───────────────────────────────────────────
@bp.post('/api/assign')
def api_assign_person():
    data = request.get_json() or {}
    aid  = data.get('activite_id')
    pid  = data.get('personnel_id')
    act  = data.get('action', 'assign')
    current_app.logger.debug(f"[services] api_assign_person called: aid={aid}, pid={pid}, action={act}")
    if not aid or not pid:
        abort(400)
    engine = get_raw_engine()
    assign_or_unassign_person(engine, aid, pid, act)
    current_app.logger.debug("[services] api_assign_person completed")
    return jsonify(status='ok'), 201

# ─── API : Mise à jour  ───────────────────────────────────────────
@bp.put('/api/activities/<int:aid>')
def move_activity(aid):
    d = request.get_json() or {}
    new_date = d.get("date_real")
    old_pid  = d.get("old_personnel_id")
    new_pid  = d.get("new_personnel_id")
    if not new_date or not old_pid or not new_pid:
        abort(400, "Il manque date_real, old_personnel_id ou new_personnel_id")
    engine = get_raw_engine()
    svc_move_activity(engine, aid, new_date, old_pid, new_pid)
    current_app.logger.debug(f"[services] update_activity moved {aid} from {old_pid} to {new_pid} on {new_date}")
    return jsonify(status="ok"), 200

@bp.put('/api/activities/<int:aid>/update')
def update_activity(aid):
    data = request.get_json() or {}

    allowed_fields = {"titre", "commentaire"}
    if not any(f in data for f in allowed_fields):
        abort(400, "Aucun champ modifiable fourni")

    engine = get_raw_engine()

    try:
        update_activity_fields(engine, aid, data)
    except ValueError as e:
        abort(400, str(e))
    except Exception as e:
        current_app.logger.error(f"Erreur mise à jour activité {aid} : {e}")
        abort(500, "Erreur serveur")

    return jsonify(status="ok"), 200

# ─── API : Suppression ───────────────────────────────────────────
@bp.delete('/api/activities/<int:aid>')
def delete_activity(aid):
    engine = get_raw_engine()
    svc_delete_activity(engine, aid)
    return jsonify(status="deleted"), 200

# ─── API : Actualisation du statut  ───────────────────────────────────────────
@bp.post('/api/activities/<int:activity_id>/status')
def update_status(activity_id):
    d = request.get_json() or {}
    new_status = d.get("statut")
    if not new_status:
        abort(400, description="Statut manquant")
    engine = get_raw_engine()
    update_activity_status(engine, activity_id, new_status)
    current_app.logger.debug(f"[services] Statut activité {activity_id} mis à jour ➔ {new_status}")
    return jsonify(status="ok")

# ─── API : Changer l'ordre ───────────────────────────────────────────
@bp.post('/api/activities/reorder')
def api_reorder_activities():
    data = request.get_json()
    personnel_id = data.get('personnel_id')
    date = data.get('date')
    ordered_activities = data.get('ordered_activities')

    if not personnel_id or not date or not ordered_activities:
        return jsonify({"error": "Missing data"}), 400

    engine = get_raw_engine()
    try:
        reorder_activities(engine, ordered_activities)
        return jsonify({"message": "Priorités mises à jour avec succès"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── API : Création de renforts  ───────────────────────────────────────────
@bp.post("/api/renfort")
def add_renfort():
    try:
        data = request.get_json()
        nom_complet = data.get("nom_complet")
        date_debut = data.get("date_debut")
        date_fin = data.get("date_fin")
        service_code = data.get("service_code")
        equipe = data.get("equipe")

        if not nom_complet or not date_debut or not date_fin or not service_code or not equipe:
            abort(400, "Champs manquants")

        service_code = service_code.upper()

        engine = get_raw_engine()
        # Utiliser la fonction qui gère réactivation + création
        personnel_id = add_or_reactivate_renfort(engine, nom_complet, date_debut, date_fin, service_code, equipe)

        current_app.logger.info(f"✅ Renfort inséré ou réactivé avec succès : {nom_complet}")
        return jsonify(status="ok", personnel_id=personnel_id), 201

    except Exception as e:
        current_app.logger.error(f"❌ Erreur dans /api/renfort : {e}")
        return jsonify({"error": str(e)}), 500

# ─── API : Gestion des renforts  ───────────────────────────────────────────
#Affiche les renforts sur le planning
@bp.get('/api/renforts')
def get_renforts():
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    service_code = request.args.get('service_key')  # <-- récupérer ici le service_key

    if not date_from or not date_to or not service_code:
        current_app.logger.error("Paramètres 'from', 'to' et 'service_key' manquants dans /api/renforts")
        abort(400, "Paramètres 'from', 'to' et 'service_key' requis")

    current_app.logger.info(f"Chargement renforts de {date_from} à {date_to} pour service {service_code}")
    engine = get_raw_engine()
    try:
        renforts = fetch_renforts(engine, date_from, date_to, service_code)  # <-- passer service_code ici
        current_app.logger.info(f"{len(renforts)} renfort(s) chargés")
        return jsonify(renforts)
    except Exception as e:
        current_app.logger.error(f"Erreur lors du fetch renforts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


#Affiche les renforts dans le modal
@bp.get('/api/all_renforts')
def all_renforts():
    engine = get_raw_engine()
    try:
        renforts = get_all_renforts(engine)  # Appel fonction métier
        return jsonify(renforts)             # Retour JSON
    except Exception as e:
        current_app.logger.error(f"Erreur lors du chargement liste renforts: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.post('/api/renfort/<string:personnel_id>/retirer')
def retirer_renfort(personnel_id):
    engine = get_raw_engine()
    rowcount = set_renfort_inactive(engine, personnel_id)
    if rowcount == 0:
        abort(404, "Renfort non trouvé")
    return jsonify(status='ok')

@bp.post('/api/renfort/<string:personnel_id>/prolonger')
def prolonger_renfort_route(personnel_id):
    data = request.get_json() or {}
    new_date_fin = data.get('date_fin')
    if not new_date_fin:
        abort(400, "date_fin requise")

    engine = get_raw_engine()
    try:
        result = prolonger_renfort(engine, personnel_id, new_date_fin)
        if result is None:
            abort(404, "Renfort non trouvé")
    except ValueError as e:
        abort(400, str(e))

    return jsonify(status="ok")


# ─── API : Supprimer des renforts  ───────────────────────────────────────────
#@bp.delete('/api/renfort/<string:personnel_id>')
#def supprimer_renfort(personnel_id):
#    engine = get_raw_engine()
#    sql = text("""
#        DELETE FROM public."Personnel"
#        WHERE "Personnel_Id" = :personnel_id
#          AND is_renfort = true
#    """)
#    with engine.connect() as conn:
#        result = conn.execute(sql, {"personnel_id": personnel_id})
#        conn.commit()
#    if result.rowcount == 0:
#        abort(404, "Renfort non trouvé")
#    return jsonify(status='ok')

# ─── API : Affichage de la page planning  ───────────────────────────────────────────
@bp.get('/<service_key>')
def planning(service_key):
    current_app.logger.debug(f"[services] planning view called with service_key={service_key!r}")
    labels = {k.lower(): v for k, v in current_app.config.get('SERVICE_LABELS', {}).items()}
    label  = labels.get(service_key.lower())
    if not label:
        current_app.logger.warning(f"[services] unknown service_key {service_key!r}")
        abort(404)

    engine = get_raw_engine()
    view = request.args.get('view', 'week')
    month_offset = int(request.args.get("month_offset", 0))
    week_offset  = int(request.args.get("week_offset", 0))

    planning_data = get_planning_data(
        engine, service_key,
        view=view, week_offset=week_offset, month_offset=month_offset
    )

    # Pour passer start_week, month_label etc au template
    return render_template(
        'planning.html',
        service_key    = service_key,
        service_label  = label,
        **planning_data
    )
