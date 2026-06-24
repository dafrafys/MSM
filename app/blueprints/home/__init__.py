from flask import Blueprint

bp = Blueprint(
    "home",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/home/static"
)

from . import routes  # important pour lier les routes à ce blueprint
