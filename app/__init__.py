# Fichier : app/__init__.py
from flask import Flask

# On importe les blueprints créés par l'équipe
from app.portail_client.routes import client_bp
from app.portail_admin.routes import admin_bp
from app.portail_auth.routes import auth_bp

def create_app():
    app = Flask(__name__)
    
    # Configurations basiques (Base de données, clé secrète...)
    app.config['SECRET_KEY'] = 'une_cle_secrete_pour_les_sessions'

    # On "branche" les modules à l'application principale
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin') # Astuce : ajoute automatiquement /admin devant toutes les URL de Gwenael !
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app