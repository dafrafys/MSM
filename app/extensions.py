# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from sqlalchemy import create_engine
from flask import current_app
from contextlib import contextmanager


db       = SQLAlchemy()
csrf     = CSRFProtect()
migrate  = Migrate()

_engine = None

def get_raw_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
    return _engine

@contextmanager
def get_conn():
    with get_raw_engine().connect() as conn:
        yield conn
