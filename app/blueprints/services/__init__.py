# app/blueprints/services/__init__.py
from flask import Blueprint

# app/blueprints/services/__init__.py
bp = Blueprint(
    'services',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/services'  # juste /services au lieu de /services/static
)


from . import routes
