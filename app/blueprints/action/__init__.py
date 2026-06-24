from flask import Blueprint

bp = Blueprint(
    "action",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/action"
)

from . import routes  # import après création de bp
