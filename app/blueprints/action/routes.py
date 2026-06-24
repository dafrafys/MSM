from flask import Blueprint, render_template, jsonify, request
from . import bp
import pandas as pd
# from scripts.etl.plan_action import load_plan_actions
from scripts.services.plan_action import insert_plan_action, get_plan_actions_for_personnel, update_plan_action, get_all_plan_actions, get_all_personnel, delete_plan_action
from app.extensions import get_raw_engine

@bp.route('/api/personnel')
def api_personnel():
    engine = get_raw_engine()
    data = get_all_personnel(engine)
    return jsonify(data)

@bp.route('/api/plan-actions')
def api_plan_actions():
    engine = get_raw_engine()
    date_cloture = request.args.get('date_cloture')

    if date_cloture == "cloture":
        data = get_all_plan_actions(engine, filter_date_cloture_null=False)
    else:
        data = get_all_plan_actions(engine, filter_date_cloture_null=True)

    return jsonify(data)

@bp.route('/api/plan-actions', methods=['POST'])
def api_insert_or_update_plan_action():
    engine = get_raw_engine()
    data = request.json or {}
    plan_id = data.get('plan_id')
    if plan_id:
        success, msg = update_plan_action(engine, data)
    else:
        success, msg = insert_plan_action(engine, data)
    status = 201 if success else 400
    return jsonify({"success": success, "message": msg}), status

@bp.route('/api/plan-actions/<personnel_id>', methods=['GET'])
def api_get_plan_actions(personnel_id):
    engine = get_raw_engine()
    plans = get_plan_actions_for_personnel(engine, personnel_id)
    return jsonify(plans)

@bp.route('/api/plan-actions/<int:plan_id>', methods=['DELETE'])
def api_delete_plan_action(plan_id):
    engine = get_raw_engine()
    success, message = delete_plan_action(engine, plan_id)
    status = 200 if success else 404
    return jsonify({"success": success, "message": message}), status

@bp.route('/plan-action')
def plan_action():
    return render_template('plan_action.html')
