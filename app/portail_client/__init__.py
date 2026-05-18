# Fichier : portail_client/routes.py
from flask import Blueprint, render_template

# 1. On crée le blueprint (nom, module d'importation)
client_bp = Blueprint('client', __name__)

# 2. Au lieu de @app.route, on utilise @client_bp.route
@client_bp.route('/')
def accueil():
    return render_template('client/accueil.html')

@client_bp.route('/reserver')
def reserver():
    return render_template('client/reserver.html')