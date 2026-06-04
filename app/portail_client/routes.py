"""
Routes client : recherche vols, détail vol, panier, checkout, historique réservations.
Gère le profil, modifications de réservation et gestion de compte.
"""

from flask import Blueprint, render_template

from .models_client import Aeroport


# Blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client')


@client_bp.route('/')
def accueil():
    """Accueil"""
    # Données simples simulées : prêtes à être remplacées par une requête SQLAlchemy
    loyalty_info = {
        'status': 'Gold Member',
        'points': '12 450',
        'flights_year': 8,
        'progress_percent': 75,
        'points_to_next': '2 550',
        'next_tier': 'Platinum'
    }

    next_flight = {
        'flight_number': 'AF712',
        'date': '14 Juin 2026',
        'status': 'Confirmé',
        'dep_time': '10:30',
        'dep_iata': 'CDG',
        'dep_city': 'Paris',
        'arr_time': '12:35',
        'arr_iata': 'FCO',
        'arr_city': 'Rome',
        'seat': 'Non assigné',
        'meal': 'Standard',
        'baggage': '1 bagage cabine + 1 bagage soute.'
    }
    
    return render_template('client/acceuil.html', loyalty_info=loyalty_info, next_flight=next_flight)

@client_bp.route('/profil')
def profil():
    """Profil"""
    return render_template('client/profil.html')

@client_bp.route('/booking')
def booking():
    """Réservation"""
    aeroports = Aeroport.query.order_by(Aeroport.ville.asc()).all()
    return render_template('client/reserver.html', aeroports=aeroports)

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
    # Données simulées : prêtes à être remplacées par "Reservation.query.filter_by(user_id=...).all()"
    reservations = [
        {
            'flight_number': 'AF712',
            'date': '14 Juin 2026',
            'status_text': "À l'heure",
            'status_class': 'status-ontime',
            'dep_time': '10:30',
            'dep_iata': 'CDG',
            'dep_city': 'Paris',
            'arr_time': '12:35',
            'arr_iata': 'FCO',
            'arr_city': 'Rome',
            'is_delayed': False,
            'is_direct': True,
            'terminal': '2F',
            'seat': '12A',
            'meal': 'Standard',
            'meal_icon': 'fa-utensils',
            'meal_color': 'var(--primary)',
            'baggage': '2 en soute',
            'baggage_icon': 'fa-suitcase-rolling',
            'baggage_color': 'var(--primary)',
            'pnr': 'X8B9Q2'
        },
        {
            'flight_number': 'AF1409',
            'date': '20 Août 2026',
            'status_text': 'Retardé',
            'status_class': 'status-delayed',
            'dep_time': '16:15',
            'original_dep_time': '15:45',
            'dep_iata': 'CDG',
            'dep_city': 'Paris',
            'arr_time': '20:45',
            'original_arr_time': '20:15',
            'arr_iata': 'FCO',
            'arr_city': 'Rome',
            'is_delayed': True,
            'is_direct': False,
            'stopover': '1 Escale: AMS (1h15)',
            'terminal': '2E',
            'seat': '24C',
            'meal': 'Végétarien',
            'meal_icon': 'fa-leaf',
            'meal_color': 'var(--flighty-green)',
            'baggage': '0 en soute',
            'baggage_icon': 'fa-suitcase-rolling',
            'baggage_color': 'var(--flighty-gray)',
            'pnr': 'A1C2E3'
        }
    ]
    
    return render_template('client/mes_reservations.html', reservations=reservations)

@client_bp.route('/gerer-reservation', methods=['GET', 'POST'])
def gerer_reservation():
    """Gérer la réservation"""
    # Données simulées pour la gestion d'une réservation spécifique
    reservation = {
        'flight_number': 'AF712',
        'arr_city': 'Rome',
        'arr_iata': 'FCO',
        'pnr': 'X8B9Q2',
        'seat': '12A',
        'seat_details': 'Business, Hublot',
        'seat_class': 'is-primary',
        'meal': 'Standard',
        'meal_class': 'is-info',
        'baggage': '2 bagages en soute (23kg max)'
    }
    return render_template('client/gerer_reservation.html', reservation=reservation)