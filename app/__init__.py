# Fichier : app/__init__.py
import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from sqlalchemy import text
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Initialiser SQLAlchemy (vide d'abord, sera lié à l'app après)
db = SQLAlchemy()
# Initialiser Flask-Mail
mail = Mail()

def create_app():
    # Spécifier le chemin du dossier static situé dans le répertoire app/
    app = Flask(
        __name__,
        static_folder='static',
        static_url_path='/static'
    )
    
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
    
    # ========== CONFIGURATION EMAIL ==========
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your_email@gmail.com')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your_password')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@obuffair.com')
    app.config['SERVER_URL'] = os.getenv('SERVER_URL', 'http://localhost:5000')
    
    # ========== INITIALISER LA DB ==========
    db.init_app(app)
    
    # ========== INITIALISER MAIL ==========
    mail.init_app(app)

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