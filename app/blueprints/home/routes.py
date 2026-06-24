from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from . import bp
from sqlalchemy import text
from datetime import date, timedelta, datetime

from app.extensions import get_raw_engine
from scripts.services.etl_orchestrator import run_etl_pipeline
from scripts.services.huddle_home import get_huddle_home_context, get_impacts, get_impact_details, insert_carte_stop, upsert_suivi_hebdo_cs, get_ratio_cartes_stop_hebdo
from scripts.services.notes import ajouter_note
from scripts.services.plan_action import insert_plan_action


# Huddle Home principal – données du tableau de bord

@bp.get("/")
def huddle_home():
    engine = get_raw_engine()
    session_date_str = request.args.get("date_session")
    month_year_str = request.args.get("month_year")  # Nouveau paramètre mois/année
    sid = session.get("current_session_id")  # valeur par défaut

    from app.config import Config  # pour objectif
    from scripts.services.utils import get_month_name_fr  # ton utilitaire

    session_date_display = None
    no_session_found = False

    # Gestion session par date
    if session_date_str:
        try:
            session_date = pd.to_datetime(session_date_str).date()
            result = pd.read_sql(
                """
                SELECT "Session_Id", date_session
                FROM public."Huddle_Session"
                WHERE date_session::date = %(session_date)s
                ORDER BY "Session_Id" DESC
                LIMIT 1
                """, engine, params={"session_date": session_date}
            )
            if not result.empty:
                sid = result.iloc[0]["Session_Id"]
                session_date_display = result.iloc[0]["date_session"]
                no_session_found = False
                session["current_session_id"] = sid
            else:
                sid = None
                session_date_display = session_date
                no_session_found = True
        except Exception as e:
            current_app.logger.exception("Erreur lors de la récupération de la session par date")
            sid = None
            session_date_display = None
            no_session_found = True

    # Gestion du filtre mois/année
    if month_year_str:
        try:
            year, month = map(int, month_year_str.split('-'))
        except Exception:
            today = date.today()
            year, month = today.year, today.month
    else:
        today = date.today()
        year, month = today.year, today.month

    selected_month_year = f"{year:04d}-{month:02d}"
    month_name = get_month_name_fr(selected_month_year)

    context = get_huddle_home_context(engine, sid=sid, session_date_str=session_date_str, config=Config, year=year, month=month)
    context.update({
        "session_date": session_date_display,
        "no_session_found": no_session_found,
        "session_id": sid,
        "selected_month_year": selected_month_year,
        "month_name": month_name,
    })

    return render_template("HuddleHome.html", **context)


@bp.post('/submit-carte-stop')
def submit_carte_stop():
    engine = get_raw_engine()
    session_id = session.get("current_session_id")
    personnel_id = request.form.get("personnel_id")
    date_realisation = request.form.get("date_realisation") or date.today().isoformat()

    current_app.logger.info(f"submit_carte_stop called with session_id={session_id}, personnel_id={personnel_id}, date={date_realisation}")

    if not all([session_id, personnel_id]):
        flash("Session ou personnel non spécifié.", "error")
        return redirect(url_for("home.huddle_home"))

    try:
        insert_carte_stop(engine, session_id, personnel_id, date_realisation)
        flash("Carte stop quotidienne enregistrée.", "success")
    except Exception as e:
        current_app.logger.exception("Erreur insertion carte stop")
        flash(f"Erreur lors de l'enregistrement : {e}", "error")

    return redirect(url_for("home.huddle_home"))


@bp.post('/submit-carte-stop-hebdo')
def submit_carte_stop_hebdo():
    engine = get_raw_engine()

    today_name = calendar.day_name[date.today().weekday()]
    if today_name != "Wednesday":
        flash("La saisie hebdomadaire n’est possible que le mercredi.", "error")
        return redirect(url_for("home.huddle_home"))

    service_code = request.form.get("service_code")
    nombre_OT = request.form.get("nombre_OT")
    semaine_annee = datetime.today().strftime("%G-W%V")

    if not service_code or nombre_OT is None:
        flash("Service ou nombre d'opérations non renseigné.", "error")
        return redirect(url_for("home.huddle_home"))

    try:
        nombre_OT_int = int(nombre_OT)
    except ValueError:
        flash("Le nombre d'opérations doit être un nombre entier.", "error")
        return redirect(url_for("home.huddle_home"))

    try:
        upsert_suivi_hebdo_cs(engine, service_code, semaine_annee, nombre_OT_int)
        flash("Donnée hebdomadaire enregistrée/mise à jour.", "success")
    except Exception as e:
        current_app.logger.exception("Erreur insertion suivi hebdo")
        flash(f"Erreur lors de l'enregistrement : {e}", "error")

    return redirect(url_for("home.huddle_home"))

@bp.post('/start-session')
def start_session():
    engine = get_raw_engine()
    try:
        # Création session + BBS (identique)
        with engine.begin() as conn:
            new_session_id = conn.execute(text("""
                INSERT INTO "Huddle_Session" ("date_session")
                VALUES (current_timestamp)
                RETURNING "Session_Id"
            """)).scalar()
            new_bbs_id = conn.execute(text("""
                INSERT INTO "BBS" ("Session_Id", "Progression_BBS")
                VALUES (:sid, 0)
                RETURNING "BBS_Id"
            """), {"sid": new_session_id}).scalar()
        session["current_session_id"] = new_session_id

        # Orchestration ETL : version native (préférée)
        try:
            run_etl_pipeline(new_session_id)
        except Exception as e:
            current_app.logger.exception("Erreur dans l'exécution du pipeline ETL")
            return jsonify({
                "status": "error",
                "step": "ETL",
                "message": str(e)
            }), 500

        return jsonify({"status": "success", "Session_Id": new_session_id}), 200

    except Exception as e:
        current_app.logger.exception("Erreur start_session")
        return jsonify({"status": "error", "step": "DB", "message": str(e)}), 500

@bp.get("/cards/<period>/<secteur>")
def cards(period, secteur):
    logger = current_app.logger
    logger.debug(f"Route /cards appelée avec period={period}, secteur={secteur}")

    engine = get_raw_engine()
    today = date.today()
    if secteur not in ("fibrage", "finissage"):
        logger.warning(f"Secteur invalide reçu : {secteur}")
        return abort(404)
    if period == "month":
        impacts_fibrage, impacts_finissage = get_impacts(
            engine, session.get("current_session_id"),
            year=today.year, month=today.month
        )
    elif period == "31days":
        start_date = today - timedelta(days=30)
        end_date = today
        impacts_fibrage, impacts_finissage = get_impacts(
            engine, session.get("current_session_id"),
            start_date=start_date, end_date=end_date
        )
    else:
        logger.warning(f"Période invalide reçue : {period}")
        return abort(404)
    impacts = impacts_fibrage if secteur == "fibrage" else impacts_finissage

    # Log des impacts récupérés
    logger.debug(f"Nombre d'impacts récupérés pour secteur '{secteur}': {len(impacts)}")
    for imp in impacts[:10]:  # afficher les 10 premiers impacts pour ne pas saturer
        logger.debug(f"Impact ID {imp.get('impact_id', 'N/A')} - pertes: {imp.get('pertes', [])}")

    return render_template("partials/impact_cards.html", impacts=impacts)


@bp.post('/submit-note')
def submit_note():
    engine = get_raw_engine()
    current_session_id = session.get("current_session_id")
    type_note         = request.form.get("Type_note")
    information       = request.form.get("Information")

    if not all([current_session_id, type_note, information]):
        flash("Toutes les données ne sont pas présentes", "error")
        return redirect(url_for("home.huddle_home"))

    try:
        ajouter_note(engine, current_session_id, type_note, information)
        flash("La note a été enregistrée avec succès.", "success")
    except Exception as e:
        flash(f"Erreur lors de l'insertion de la note : {e}", "error")

    return redirect(url_for("home.huddle_home"))


@bp.post('/update_plan_action')
def update_plan_action():
    engine = get_raw_engine()
    excel_ok, excel_msg = insert_plan_action(engine, request.form)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if excel_ok:
            return jsonify({"status": "success", "excel_ok": True, "excel_msg": excel_msg})
        else:
            return jsonify({"status": "error", "excel_msg": excel_msg}), 500
    if excel_ok:
        flash("Plan d’action enregistré avec succès.", "success")
    else:
        flash(f"Erreur lors de l'enregistrement : {excel_msg}", "error")
    return redirect(url_for("home.huddle_home"))


@bp.get('/api/impact/<int:impact_id>')
def api_get_impact(impact_id):
    engine = get_raw_engine()
    impact = get_impact_details(engine, impact_id)
    if not impact:
        return jsonify({"error": "Impact non trouvé"}), 404
    return jsonify({"impact": impact})
