import os
from pathlib import Path

basedir = Path(__file__).parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-fallback-secret-key-12345'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + str(basedir / 'instance' / 'foodwise.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
