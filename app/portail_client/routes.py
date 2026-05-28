"""
Routes client : recherche vols, détail vol, panier, checkout, historique réservations.
Gère le profil, modifications de réservation et gestion de compte.
"""

from flask import Blueprint, render_template


# Blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client')


@client_bp.route('/')
def accueil():
    """Accueil"""
    return render_template('client/acceuil.html')

@client_bp.route('/profil')
def profil():
    """Profil"""
    return render_template('client/profil.html')

@client_bp.route('/booking')
def booking():
    """Réservation"""
    return render_template('client/reserver.html')

@client_bp.route('/booking-flights', methods=['GET', 'POST'])
def booking_flights():
    """Sélection vol"""
    return render_template('client/booking_flights.html')

@client_bp.route('/booking-passengers', methods=['GET', 'POST'])
def booking_passengers():
    """Information passager"""
    return render_template('client/booking_passengers.html')

@client_bp.route('/booking-options', methods=['GET', 'POST'])
def booking_options():
    """Options"""
    return render_template('client/booking_options.html')

@client_bp.route('/booking-payment', methods=['GET', 'POST'])
def booking_payment():
    """Payement"""
    return render_template('client/booking_payment.html')

@client_bp.route('/mes-reservations', methods=['GET', 'POST'])
def mes_reservations():
    """Mes réservations"""
    return render_template('client/mes_reservations.html')

@client_bp.route('/gerer-reservation', methods=['GET', 'POST'])
def gerer_reservation():
    """Gérer la réservation"""
    return render_template('client/gerer_reservation.html')