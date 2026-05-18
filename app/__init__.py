# Fichier : app/__init__.py
import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialiser SQLAlchemy (vide d'abord, sera lié à l'app après)
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    
    # ========== CONFIGURATION ==========
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'
    
    # Base de données MySQL distante
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://gwenael.drouet:password@enac.darties.fr/gwenael.drouet_Projet_obuffair'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'connect_timeout': 5}
    }
    
    # ========== INITIALISER LA DB ==========
    db.init_app(app)

    # ========== ENREGISTRER LES BLUEPRINTS ==========
    from app.portail_auth.routes import auth_bp
    from app.portail_admin.routes import admin_bp
    from app.portail_client.routes import client_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(client_bp)

    @app.route('/')
    def index():
        return {'message': 'Bienvenue sur Obuffair!', 'status': 'OK'}
    
    @app.route('/styleguide')
    def styleguide():
        """Afficher la charte UI / Design System"""
        return render_template('styleguide.html', now=datetime.now())
    
    return app