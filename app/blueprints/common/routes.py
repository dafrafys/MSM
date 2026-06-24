# app/common/routes.py
from flask import Blueprint, jsonify, current_app
from collections import deque
import os, itertools

bp = Blueprint('common', __name__)

def get_log_file_path():
    # construit dynamiquement le chemin à partir du contexte application
    return os.path.abspath(
        os.path.join(current_app.root_path, os.pardir, 'huddle_tasks.log')
    )

@bp.route('/api/logs')
def api_get_logs():
    log_file = get_log_file_path()
    if not os.path.exists(log_file):
        return jsonify(logs=[])
    with open(log_file, encoding='utf-8', errors='ignore') as f:
        # garde les 50 dernières lignes
        lines = deque(itertools.islice(f, None), maxlen=50)
    return jsonify(logs=list(lines))

@bp.route('/api/clear_logs', methods=['POST'])
def api_clear_logs():
    log_file = get_log_file_path()
    try:
        # tronque le fichier
        open(log_file, 'w', encoding='utf-8').close()
        return jsonify(status='ok')
    except Exception as e:
        current_app.logger.exception("Impossible de vider les logs")
        return jsonify(status='error', message=str(e)), 500
