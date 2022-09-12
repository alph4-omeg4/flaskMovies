import os
import pathlib
import secrets

BASE_DIR = pathlib.Path(__file__).parent


class Config:
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASEQ_URL') or 'sqlite:///' + str(BASE_DIR / "data" / "flaskTest.sqlite3")
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASEQ_URL') or 'sqlite:///' + str(
        BASE_DIR / "data" / "flaskTest.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = secrets.token_hex(16)
