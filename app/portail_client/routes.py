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

@client_bp.route('/profil')
def profil():
    """Page de profil"""
    return render_template('client/profil.html')

@client_bp.route('/booking')
def booking():
    """Page de réservation"""
    return render_template('client/reserver.html')

@client_bp.route('/booking-flights', methods=['GET', 'POST'])
def booking_flights():
    """Page de sélection de vols"""
    return render_template('client/booking_flights.html')

@client_bp.route('/booking-passengers', methods=['GET', 'POST'])
def booking_passengers():
    """Page d'informations passager"""
    return render_template('client/booking_passengers.html')

@client_bp.route('/booking-options', methods=['GET', 'POST'])
def booking_options():
    """Page des options"""
    return render_template('client/booking_options.html')

@client_bp.route('/booking-payment', methods=['GET', 'POST'])
def booking_payment():
    """Page de payment"""
    return render_template('client/booking_payment.html')