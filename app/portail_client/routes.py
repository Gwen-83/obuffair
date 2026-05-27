"""
Routes client : recherche vols, détail vol, panier, checkout, historique réservations.
Gère le profil, modifications de réservation et gestion de compte.
"""

from flask import Blueprint, render_template

# Blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client')


@client_bp.route('/')
def accueil():
    """Page d'accueil client"""
    return render_template('client/acceuil.html')


@client_bp.route('/reserver')
def reserver():
    """Page de réservation"""
    return render_template('client/reserver.html')
