"""
Routes client : recherche vols, détail vol, panier, checkout, historique réservations.
Gère le profil, modifications de réservation et gestion de compte.
"""

from functools import wraps
from flask import Blueprint, render_template, request, session, url_for, redirect, flash
from app import db
from sqlalchemy import func, cast, Date, text
from app.model import Aeroport, Vols, User, Support
from datetime import datetime, timedelta, timezone
import re


# Blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à la réservation.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

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
    
    # --- Requête pour les destinations du carrousel ---
    try:
        lowest_prices = db.session.query(
            Aeroport.ville,
            func.min(Vols.prix_de_base).label('min_prix')
        ).join(Vols, Vols.id_aeroport_arrivee == Aeroport.id_aeroport)\
         .group_by(Aeroport.ville)\
         .order_by(func.min(Vols.prix_de_base))\
         .limit(6).all()
         
        destinations = [{'ville': row.ville, 'prix': int(row.min_prix) if row.min_prix is not None else 0} for row in lowest_prices]
    except Exception as e:
        print(f"Erreur SQL Carrousel Destinations: {e}")
        destinations = []
    
    # Fallback si aucun vol n'est présent dans la BDD ou en cas d'erreur
    if not destinations:
        destinations = [
            {'ville': 'Rome', 'prix': 124},
            {'ville': 'Londres', 'prix': 98},
            {'ville': 'Madrid', 'prix': 85},
            {'ville': 'Berlin', 'prix': 110}
        ]

    return render_template('client/acceuil.html', loyalty_info=loyalty_info, next_flight=next_flight, destinations=destinations)

@client_bp.route('/profil', methods=['GET', 'POST'])
def profil():
    """Profil"""
    user_id = session.get('user_id')
    
    # Si l'utilisateur n'est pas connecté, on le redirige
    if not user_id:
        return redirect(url_for('client.accueil'))
        
    # Récupération du client en base de données
    client_connecte = db.session.get(User, user_id)
    if not client_connecte:
        return redirect(url_for('client.accueil'))
        
    if request.method == 'POST':
        client_connecte.prenom = request.form.get('prenom', client_connecte.prenom)
        client_connecte.nom = request.form.get('nom', client_connecte.nom)
        client_connecte.email = request.form.get('email', client_connecte.email)
        
        # Validation et sauvegarde du numéro de téléphone
        num_tel = request.form.get('numero_telephone')
        if num_tel and re.match(r'^\+33\d \d{2} \d{2} \d{2} \d{2}$', num_tel):
            client_connecte.numero_telephone = num_tel
        elif not num_tel: # Si le champ est vidé
            client_connecte.numero_telephone = None
            
        db.session.commit()
        session['prenom'] = client_connecte.prenom
        session['nom'] = client_connecte.nom
        flash('Vos informations ont été mises à jour avec succès.', 'success')
        return redirect(url_for('client.profil'))
        
    prochains_billets = client_connecte.get_prochains_vols()
    prochains_vols_data = []
    
    if prochains_billets:
        mois_fr = {1: 'Jan', 2: 'Fév', 3: 'Mars', 4: 'Avr', 5: 'Mai', 6: 'Juin', 
                   7: 'Juil', 8: 'Août', 9: 'Sept', 10: 'Oct', 11: 'Nov', 12: 'Déc'}
        for billet in prochains_billets:
            vol = billet.vol
            date_vol = f"{vol.date_heure_dep_utc.day} {mois_fr[vol.date_heure_dep_utc.month]} {vol.date_heure_dep_utc.year}"
            
            status_text = "À l'heure" if vol.statut.lower() == "à l'heure" else vol.statut.capitalize()
            status_class = "status-ontime" if vol.statut.lower() == "à l'heure" else "status-delayed"
            
            prochains_vols_data.append({
                'flight_number': f"OB{vol.id_vol}",
                'date': date_vol,
                'status_text': status_text,
                'status_class': status_class,
                'dep_iata': vol.id_aeroport_depart,
                'arr_iata': vol.id_aeroport_arrivee,
                'dep_time': vol.date_heure_dep_utc.strftime('%H:%M'),
                'arr_time': vol.date_heure_arr_utc.strftime('%H:%M'),
                'pnr': f"X{billet.id_reservation}B9Q{billet.id_billet}"
            })
            
    return render_template('client/profil.html', client=client_connecte, prochains_vols=prochains_vols_data)

@client_bp.route('/support', methods=['GET', 'POST'])
def support():
    """Formulaire de ticket de support client"""
    user_info = {}
    user_id = session.get('user_id', 0)
    if user_id:
        user_record = db.session.get(User, user_id)
        if user_record:
            user_info = {
                'nom': f"{user_record.prenom or ''} {user_record.nom or ''}".strip(),
                'email': user_record.email
            }

    form_data = {
        'titre': request.form.get('titre', '') if request.method == 'POST' else '',
        'categorie': request.form.get('categorie', 'reservation') if request.method == 'POST' else 'reservation',
        'priorite': request.form.get('priorite', 'normale') if request.method == 'POST' else 'normale',
        'description': request.form.get('description', '') if request.method == 'POST' else '',
        'nom_contact': request.form.get('nom_contact', '') if request.method == 'POST' else (user_info.get('nom') if user_info else ''),
        'email_contact': request.form.get('email_contact', '') if request.method == 'POST' else (user_info.get('email') if user_info else '')
    }

    if request.method == 'POST':
        titre = form_data['titre'].strip()
        categorie = form_data['categorie'] or 'autre'
        priorite = form_data['priorite'] or 'normale'
        description = form_data['description'].strip()

        if not titre or not description:
            flash('Veuillez renseigner un titre et une description pour votre ticket.', 'danger')
        else:
            if not user_info:
                contact_name = form_data['nom_contact'].strip() or 'Invité'
                contact_email = form_data['email_contact'].strip() or 'non renseigné'
                description = f"Contact invité : {contact_name} \nEmail : {contact_email}\n\n{description}"

            ticket = Support(
                id_client=user_id or 0,
                titre=titre,
                description=description,
                categorie=categorie,
                priorite=priorite,
                statut='nouveau'
            )
            try:
                db.session.add(ticket)
                db.session.commit()
                flash('Votre demande a bien été envoyée au support. Nous vous répondrons rapidement.', 'success')
                return redirect(url_for('client.support'))
            except Exception as e:
                db.session.rollback()
                flash('Une erreur est survenue lors de l’envoi de votre ticket. Veuillez réessayer.', 'danger')

    return render_template('client/ticket.html', user_info=user_info, form_data=form_data)

@client_bp.route('/booking')
@login_required
def booking():
    """Réservation"""
    aeroports = db.session.execute(text("SELECT * FROM aeroports ORDER BY ville ASC")).mappings().all()
    search_params = session.get('search_params', {})
    return render_template('client/reserver.html', aeroports=aeroports, search_params=search_params)

def format_duration(td):
    """Formate un timedelta en chaîne (ex: 2h 05m)"""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes:02d}m"

def calculate_yield_prices(legs, type_vol):
    """
    Logique de Yield Management (Pricing dynamique).
    Prend en compte : l'heure locale, les correspondances et le type de trajet.
    """
    base_price = sum(leg['prix_de_base'] for leg in legs)
    
    # 1. Discount de correspondance (Réseau Hub-and-Spoke)
    # Vol avec escale = inconfort = prix réduit pour rester compétitif
    stops = len(legs) - 1
    if stops == 1:
        base_price *= 0.85  # -15%
    elif stops >= 2:
        base_price *= 0.75  # -25%
        
    # 2. Yield management basé sur le temps avant le départ
    # Utilisation de l'heure locale de la machine pour plus de précision
    first_leg_local = legs[0]['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
    time_to_dep = first_leg_local.replace(tzinfo=None) - datetime.now()
    days_to_dep = time_to_dep.days
    
    if days_to_dep <= 3:
        yield_multiplier = 1.8  # J-3 : Forte demande (+80%)
    elif days_to_dep <= 7:
        yield_multiplier = 1.4  # J-7 : Dernière minute (+40%)
    elif days_to_dep <= 14:
        yield_multiplier = 1.15 # J-14 : Remplissage (+15%)
    elif days_to_dep >= 60:
        yield_multiplier = 0.9  # J-60 : Achat en avance (-10%)
    else:
        yield_multiplier = 1.0  # Tarif standard
        
    # 3. Discount Aller-Retour (Fidélisation)
    ar_multiplier = 0.9 if type_vol == 'AR' else 1.0  # -10% si A/R
    
    # Calcul final avec un prix plancher à 50€
    final_eco = max(50, int(base_price * yield_multiplier * ar_multiplier)) 
    
    return {
        'eco': final_eco,
        'biz': int(final_eco * 2.5),
        'first': int(final_eco * 4)
    }

def search_itineraries(origin, destination, target_date_str, max_stops=2):
    """Algorithme de recherche avec filtrage par date locale de la machine"""
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return []

    valid_itineraries = []
    
    # Requête large en BDD : +/- 1 jour pour compenser les décalages horaires UTC vs Local
    start_bound = target_date - timedelta(days=1)
    end_bound = target_date + timedelta(days=2)

    # 1. Vols Directs
    direct_flights = db.session.execute(text("""
        SELECT * FROM vols 
        WHERE id_aeroport_depart = :origin 
        AND id_aeroport_arrivee = :destination
        AND DATE(date_heure_dep_utc) >= :start_bound
        AND DATE(date_heure_dep_utc) < :end_bound
    """), {
        'origin': origin,
        'destination': destination,
        'start_bound': start_bound,
        'end_bound': end_bound
    }).mappings().all()
    
    for f in direct_flights:
        # Filtrage exact sur le fuseau horaire local de la machine
        f_local = f['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
        if f_local.date() == target_date:
            valid_itineraries.append([f])

    # 2. Vols avec 1 Escale
    if max_stops >= 1:
        first_legs = db.session.execute(text("""
            SELECT * FROM vols 
            WHERE id_aeroport_depart = :origin 
            AND id_aeroport_arrivee != :destination
            AND DATE(date_heure_dep_utc) >= :start_bound
            AND DATE(date_heure_dep_utc) < :end_bound
        """), {
            'origin': origin,
            'destination': destination,
            'start_bound': start_bound,
            'end_bound': end_bound
        }).mappings().all()
        
        for leg1 in first_legs:
            leg1_local = leg1['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
            if leg1_local.date() != target_date:
                continue
                
            min_dep = leg1['date_heure_arr_utc'] + timedelta(minutes=45) # Escale min
            max_dep = leg1['date_heure_arr_utc'] + timedelta(hours=12)   # Escale max
            
            second_legs = db.session.execute(text("""
                SELECT * FROM vols 
                WHERE id_aeroport_depart = :origin 
                AND id_aeroport_arrivee = :destination
                AND date_heure_dep_utc >= :min_dep
                AND date_heure_dep_utc <= :max_dep
            """), {
                'origin': leg1['id_aeroport_arrivee'],
                'destination': destination,
                'min_dep': min_dep,
                'max_dep': max_dep
            }).mappings().all()
            
            for leg2 in second_legs:
                valid_itineraries.append([leg1, leg2])
                
                # 3. Vols avec 2 Escales (Extension de leg2)
                if max_stops >= 2:
                    min_dep2 = leg2['date_heure_arr_utc'] + timedelta(minutes=45)
                    max_dep2 = leg2['date_heure_arr_utc'] + timedelta(hours=12)
                    third_legs = db.session.execute(text("""
                        SELECT * FROM vols 
                        WHERE id_aeroport_depart = :origin 
                        AND id_aeroport_arrivee = :destination
                        AND date_heure_dep_utc >= :min_dep
                        AND date_heure_dep_utc <= :max_dep
                    """), {
                        'origin': leg2['id_aeroport_arrivee'],
                        'destination': destination,
                        'min_dep': min_dep2,
                        'max_dep': max_dep2
                    }).mappings().all()
                    
                    for leg3 in third_legs:
                        valid_itineraries.append([leg1, leg2, leg3])

    return valid_itineraries

@client_bp.route('/booking-flights', methods=['GET', 'POST'])
@login_required
def booking_flights():
    """Sélection vol"""
    if request.method == 'POST':
        # S'il clique sur "Changer le vol aller"
        if 'reset_aller' in request.form:
            session.pop('vol_aller', None)
            
        # Nouvelle recherche depuis reserver.html
        elif 'type_vol' in request.form:
            session['search_params'] = request.form.to_dict()
            session.pop('vol_aller', None)
            session.pop('vol_retour', None)
            
        # Sélection temporaire du vol aller pour un A/R
        elif 'id_vol_aller_temp' in request.form:
            session['vol_aller'] = {
                'id_vol': request.form.get('id_vol_aller_temp'),
                'classe': request.form.get('classe')
            }
            
    search_params = session.get('search_params', {})
    
    if not search_params and request.method == 'GET':
        return redirect(url_for('client.booking'))
        
    type_vol = search_params.get('type_vol', 'AS')
    vol_aller_choisi = session.get('vol_aller') is not None
    
    # Détermine si on est à l'étape du choix du vol retour
    is_retour_step = (type_vol == 'AR') and vol_aller_choisi
    
    # Inverse dynamiquement le départ/arrivée si on est sur le retour
    if is_retour_step:
        iata_dep = search_params.get('arrivee', 'FCO')
        iata_arr = search_params.get('depart', 'CDG')
        date_vol_raw = search_params.get('date_retour')
        titre = "Sélectionnez votre vol retour"
    else:
        iata_dep = search_params.get('depart', 'CDG')
        iata_arr = search_params.get('arrivee', 'FCO')
        date_vol_raw = search_params.get('date_aller')
        titre = "Sélectionnez votre vol aller"

    # 1. Obtenir les noms des villes
    aero_dep = db.session.execute(text("SELECT ville FROM aeroports WHERE id_aeroport = :iata"), {'iata': iata_dep}).fetchone()
    aero_arr = db.session.execute(text("SELECT ville FROM aeroports WHERE id_aeroport = :iata"), {'iata': iata_arr}).fetchone()
    ville_dep = aero_dep[0] if aero_dep else iata_dep
    ville_arr = aero_arr[0] if aero_arr else iata_arr
    
    date_vol = datetime.strptime(date_vol_raw, '%Y-%m-%d').strftime('%d/%m/%Y') if date_vol_raw else 'Date invalide'
    
    # 2. Exécuter l'algorithme
    raw_itineraries = search_itineraries(iata_dep, iata_arr, date_vol_raw)
    all_airports_rows = db.session.execute(text("SELECT id_aeroport, ville FROM aeroports")).fetchall()
    all_airports = {row[0]: row[1] for row in all_airports_rows}
    
    itineraries_data = []
    for legs in raw_itineraries:
        # Conversion des heures extrêmes en heure locale de la machine
        dep_time_local = legs[0]['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
        arr_time_local = legs[-1]['date_heure_arr_utc'].replace(tzinfo=timezone.utc).astimezone()
        
        # Appelle notre nouveau module de Yield Management
        prices = calculate_yield_prices(legs, type_vol)
        
        segments = []
        for i, leg in enumerate(legs):
            leg_dep_local = leg['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
            leg_arr_local = leg['date_heure_arr_utc'].replace(tzinfo=timezone.utc).astimezone()
            
            layover = format_duration(legs[i+1]['date_heure_dep_utc'] - leg['date_heure_arr_utc']) if i < len(legs) - 1 else None
            segments.append({
                'flight_number': f"OB{leg['id_vol']}",
                'dep_iata': leg['id_aeroport_depart'],
                'dep_city': all_airports.get(leg['id_aeroport_depart'], leg['id_aeroport_depart']),
                'dep_time': leg_dep_local.strftime('%H:%M'),
                'arr_iata': leg['id_aeroport_arrivee'],
                'arr_city': all_airports.get(leg['id_aeroport_arrivee'], leg['id_aeroport_arrivee']),
                'arr_time': leg_arr_local.strftime('%H:%M'),
                'layover': layover
            })
            
        stops = len(legs) - 1
        itineraries_data.append({
            'id': "_".join(str(leg['id_vol']) for leg in legs),  # Ex: "12_15" pour vols 12 + 15
            'dep_time': dep_time_local.strftime('%H:%M'),
            'arr_time': arr_time_local.strftime('%H:%M'),
            'duration': format_duration(legs[-1]['date_heure_arr_utc'] - legs[0]['date_heure_dep_utc']),
            'stops_text': "Direct" if stops == 0 else f"{stops} Escale{'s' if stops > 1 else ''}",
            'stops': stops,
            'price_eco': prices['eco'],
            'price_biz': prices['biz'],
            'price_first': prices['first'],
            'segments': segments
        })
        
    # Trier par heure de départ
    itineraries_data.sort(key=lambda x: x['dep_time'])
    
    # --- Logique de Pagination (10 vols max par page) ---
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_itineraries = len(itineraries_data)
    total_pages = (total_itineraries + per_page - 1) // per_page
    
    if page < 1: page = 1
    elif page > total_pages and total_pages > 0: page = total_pages
        
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_itineraries = itineraries_data[start_idx:end_idx]

    return render_template('client/booking_flights.html',
                           search_params=search_params,
                           is_retour_step=is_retour_step,
                           iata_dep=iata_dep,
                           iata_arr=iata_arr,
                           ville_dep=ville_dep,
                           ville_arr=ville_arr,
                           date_vol=date_vol,
                           itineraries=paginated_itineraries,
                           current_page=page,
                           total_pages=total_pages,
                           titre=titre)

@client_bp.route('/booking-passengers', methods=['GET', 'POST'])
@login_required
def booking_passengers():
    """Information passager"""
    if request.method == 'POST':
        # Enregistrement du dernier vol choisi
        if 'id_vol_final' in request.form:
            vol_final = {
                'id_vol': request.form.get('id_vol_final'),
                'classe': request.form.get('classe')
            }
            search_params = session.get('search_params', {})
            
            if search_params.get('type_vol') == 'AR':
                session['vol_retour'] = vol_final
            else:
                session['vol_aller'] = vol_final
                
    return render_template('client/booking_passengers.html')

@client_bp.route('/booking-options', methods=['GET', 'POST'])
@login_required
def booking_options():
    """Options"""
    return render_template('client/booking_options.html')

@client_bp.route('/booking-payment', methods=['GET', 'POST'])
@login_required
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