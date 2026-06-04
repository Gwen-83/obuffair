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
from app.algos.search import search_itineraries
from app.algos.yield_management import calculer_prix
import re


# Blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client')

TARIFS_OPTIONS = {
    'bagages_eco': {
        '0': 0,
        '1': 45,
        '2': 80,
        '3': 115
    },
    'repas_eco': {
        'standard': 0,
        'premium': 15,
        'vegetarien': 15
    }
}

@client_bp.context_processor
def inject_tarifs():
    return dict(TARIFS_OPTIONS=TARIFS_OPTIONS)

def update_total_panier():
    search_params = session.get('search_params', {})
    if not search_params:
        session.pop('total_panier', None)
        return
    try:
        nb_passagers = int(search_params.get('passagers', 1))
    except (ValueError, TypeError):
        nb_passagers = 1
        
    prix_aller = float(session.get('vol_aller', {}).get('prix', 0)) if session.get('vol_aller') else 0.0
    prix_retour = float(session.get('vol_retour', {}).get('prix', 0)) if session.get('vol_retour') else 0.0
    prix_options = float(session.get('options', {}).get('prix', 0)) if session.get('options') else 0.0
    
    session['total_panier'] = ((prix_aller + prix_retour) + prix_options) * nb_passagers
    session.modified = True

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
            date_vol = f"{vol.date_heure_dep_utc.day:02d}-{vol.date_heure_dep_utc.month:02d}-{vol.date_heure_dep_utc.year}"
            
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
    # Si l'utilisateur clique sur le fil d'Ariane "Recherche" depuis une étape ultérieure,
    # on vide les sélections de vol et de passagers, mais on conserve les paramètres de recherche.
    if 'vol_aller' in session:
        session.pop('vol_aller', None)
        session.pop('vol_retour', None)
        session.pop('options', None)
        session.pop('passagers_data', None)
        update_total_panier()
        session.modified = True
    aeroports = db.session.execute(text("SELECT * FROM aeroports ORDER BY ville ASC")).mappings().all()
    search_params = session.get('search_params', {})
    return render_template('client/reserver.html', aeroports=aeroports, search_params=search_params)

def format_duration(td):
    """Formate un timedelta en chaîne (ex: 2h 05m)"""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes:02d}m"

@client_bp.route('/booking-flights', methods=['GET', 'POST'])
@login_required
def booking_flights():
    """Sélection vol"""
    if request.method == 'POST':
        # Changement rapide de date depuis le bouton "Aucun vol trouvé"
        if 'update_date_only' in request.form:
            if 'search_params' in session:
                new_aller = request.form.get('date_aller')
                new_retour = request.form.get('date_retour')
                
                # Failsafe: Empêcher l'inversion si la suggestion pousse l'aller après le retour
                if new_aller and new_retour:
                    try:
                        if datetime.strptime(new_retour, '%Y-%m-%d').date() < datetime.strptime(new_aller, '%Y-%m-%d').date():
                            new_retour = new_aller
                    except ValueError:
                        pass
                        
                session['search_params']['date_aller'] = new_aller
                session['search_params']['date_retour'] = new_retour
                session.modified = True
                update_total_panier()
                
        # S'il clique sur "Changer le vol aller"
        elif 'reset_aller' in request.form:
            session.pop('vol_aller', None)
            session.pop('vol_retour', None)
            session.pop('options', None)
            update_total_panier()
            
        # Nouvelle recherche depuis reserver.html
        elif 'type_vol' in request.form:
            session['search_params'] = request.form.to_dict()
            session.pop('vol_aller', None)
            session.pop('vol_retour', None)
            session.pop('options', None)
            session.pop('passagers_data', None)
            update_total_panier()
            
        # Sélection temporaire du vol aller pour un A/R
        elif 'id_vol_aller_temp' in request.form:
            session['vol_aller'] = {
                'id_vol': request.form.get('id_vol_aller_temp'),
                'classe': request.form.get('classe'),
                'classes': request.form.getlist('classes[]'),
                'prix': float(request.form.get('prix', 0)),
                'prix_eco': float(request.form.get('prix_eco', 0)),
                'prix_biz': float(request.form.get('prix_biz', 0)),
                'prix_first': float(request.form.get('prix_first', 0))
            }
            
            # Si on change de vol, on efface uniquement les sièges car l'avion change
            if 'options' in session:
                for p in session['options'].get('passagers', []):
                    p['siege'] = ''
            session.modified = True
            update_total_panier()
            
            return redirect(url_for('client.booking_flights', step='retour'))
            
        return redirect(url_for('client.booking_flights'))

    search_params = session.get('search_params', {})
    
    if not search_params and request.method == 'GET':
        return redirect(url_for('client.booking'))
        
    type_vol = search_params.get('type_vol', 'AS')
    vol_aller_choisi = session.get('vol_aller') is not None
    
    # Détermine si on est à l'étape du choix du vol retour
    step_param = request.args.get('step')
    is_retour_step = False
    
    if type_vol == 'AR':
        if step_param == 'retour':
            is_retour_step = True
        elif step_param == 'aller':
            is_retour_step = False
        elif vol_aller_choisi and not session.get('vol_retour'):
            is_retour_step = True
    
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
    
    date_vol = datetime.strptime(date_vol_raw, '%Y-%m-%d').strftime('%d-%m-%Y') if date_vol_raw else 'Date invalide'
    
    # 2. Exécuter l'algorithme
    raw_itineraries = search_itineraries(iata_dep, iata_arr, date_vol_raw)
    all_airports_rows = db.session.execute(text("SELECT id_aeroport, ville FROM aeroports")).fetchall()
    all_airports = {row[0]: row[1] for row in all_airports_rows}
    
    # Pré-chargement des capacités pour tous les segments de vol retournés
    unique_leg_ids = set(leg['id_vol'] for legs in raw_itineraries for leg in legs)
    capacities = {}
    if unique_leg_ids:
        # OPTIMISATION : Requête unique (Bulk fetch) au lieu d'une boucle (N+1 Query)
        res_caps = db.session.execute(text("""
            SELECT v.id_vol, a.eco_rang_de, a.eco_rang_a, a.bus_rang_de, a.bus_rang_a, a.first_rang_de, a.first_rang_a, a.largeur_rangee,
                   COALESCE(SUM(CASE WHEN b.classe = 'Eco' THEN 1 ELSE 0 END), 0) as sold_eco,
                   COALESCE(SUM(CASE WHEN b.classe = 'Business' THEN 1 ELSE 0 END), 0) as sold_bus,
                   COALESCE(SUM(CASE WHEN b.classe = 'First' THEN 1 ELSE 0 END), 0) as sold_first
            FROM vols v
            JOIN avions a ON v.immatriculation_avion = a.immatriculation
            LEFT JOIN billets b ON b.id_vol = v.id_vol
            WHERE v.id_vol IN :leg_ids
            GROUP BY v.id_vol, a.immatriculation
        """), {'leg_ids': tuple(unique_leg_ids)}).mappings().all()
        
        for row in res_caps:
            def cap(de, a, width): return max(0, a - de + 1) * width if a >= de > 0 else 0
            capacities[row['id_vol']] = {
                'cap_eco': cap(row['eco_rang_de'], row['eco_rang_a'], row['largeur_rangee']),
                'cap_bus': cap(row['bus_rang_de'], row['bus_rang_a'], row['largeur_rangee']),
                'cap_first': cap(row['first_rang_de'], row['first_rang_a'], row['largeur_rangee']),
                'sold_eco': int(row['sold_eco']),
                'sold_bus': int(row['sold_bus']),
                'sold_first': int(row['sold_first'])
            }

    itineraries_data = []
    for legs in raw_itineraries:
        caps = [capacities.get(leg['id_vol']) for leg in legs]
        if None in caps:
            continue # Données de capacité manquantes

        # Conversion des heures extrêmes en heure locale de la machine
        dep_time_local = legs[0]['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
        arr_time_local = legs[-1]['date_heure_arr_utc'].replace(tzinfo=timezone.utc).astimezone()
        
        # Utilisation de l'algorithme unifié de Yield Management
        total_cap = sum(c['cap_eco'] + c['cap_bus'] + c['cap_first'] for c in caps)
        total_sold = sum(c['sold_eco'] + c['sold_bus'] + c['sold_first'] for c in caps)
        taux_vol = float(total_sold) / total_cap if total_cap > 0 else 0.0
        
        cap_eco_sum = sum(c['cap_eco'] for c in caps)
        taux_eco = float(sum(c['sold_eco'] for c in caps)) / cap_eco_sum if cap_eco_sum > 0 else 0.0
        
        cap_bus_sum = sum(c['cap_bus'] for c in caps)
        taux_bus = float(sum(c['sold_bus'] for c in caps)) / cap_bus_sum if cap_bus_sum > 0 else 0.0
        
        cap_first_sum = sum(c['cap_first'] for c in caps)
        taux_first = float(sum(c['sold_first'] for c in caps)) / cap_first_sum if cap_first_sum > 0 else 0.0
        
        base_price = sum(float(leg['prix_de_base']) for leg in legs)
        stops = len(legs) - 1
        if stops == 1: base_price *= 0.85
        elif stops >= 2: base_price *= 0.75
        if type_vol == 'AR': base_price *= 0.9
        
        date_dep = legs[0]['date_heure_dep_utc']
        now = datetime.utcnow()
        
        p_eco = calculer_prix(base_price, date_dep, now, taux_vol, taux_eco, 'eco')['prix_final']
        p_biz = calculer_prix(base_price * 2.5, date_dep, now, taux_vol, taux_bus, 'business')['prix_final']
        p_first = calculer_prix(base_price * 4.0, date_dep, now, taux_vol, taux_first, 'first')['prix_final']
        
        prices = {
            'eco': max(50, int(p_eco)),
            'biz': int(p_biz),
            'first': int(p_first)
        }
        
        segments = []
        for i, leg in enumerate(legs):
            leg_dep_local = leg['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
            leg_arr_local = leg['date_heure_arr_utc'].replace(tzinfo=timezone.utc).astimezone()
            
            layover_td = legs[i+1]['date_heure_dep_utc'] - leg['date_heure_arr_utc'] if i < len(legs) - 1 else None
            layover = format_duration(layover_td) if layover_td else None
            is_short_layover = (layover_td < timedelta(minutes=60)) if layover_td else False
            segments.append({
                'flight_number': f"OB{leg['id_vol']}",
                'dep_iata': leg['id_aeroport_depart'],
                'dep_city': all_airports.get(leg['id_aeroport_depart'], leg['id_aeroport_depart']),
                'dep_time': leg_dep_local.strftime('%H:%M'),
                'arr_iata': leg['id_aeroport_arrivee'],
                'arr_city': all_airports.get(leg['id_aeroport_arrivee'], leg['id_aeroport_arrivee']),
                'arr_time': leg_arr_local.strftime('%H:%M'),
                'layover': layover,
                'is_short_layover': is_short_layover
            })
            
        stops = len(legs) - 1
        
        avail_eco = min(max(0, c['cap_eco'] - c['sold_eco']) for c in caps)
        avail_bus = min(max(0, c['cap_bus'] - c['sold_bus']) for c in caps)
        avail_first = min(max(0, c['cap_first'] - c['sold_first']) for c in caps)
        
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
            'avail_eco': avail_eco, 'cap_eco': min(c['cap_eco'] for c in caps),
            'avail_biz': avail_bus, 'cap_biz': min(c['cap_bus'] for c in caps),
            'avail_first': avail_first, 'cap_first': min(c['cap_first'] for c in caps),
            'segments': segments
        })
        
    # Trier par heure de départ
    itineraries_data.sort(key=lambda x: x['dep_time'])
    
    # --- Recherche de jusqu'à 3 dates alternatives si aucun vol ---
    alternative_vols = []
    
    if not itineraries_data and date_vol_raw:
        try:
            base_date = datetime.strptime(date_vol_raw, '%Y-%m-%d').date()
            
            # Si on est sur le vol retour, on ne peut pas proposer une date AVANT le vol aller
            min_date = datetime.now().date()
            if is_retour_step and search_params.get('date_aller'):
                min_date = max(min_date, datetime.strptime(search_params.get('date_aller'), '%Y-%m-%d').date())
                
            # On cherche à -1 jour et jusqu'à +7 jours (trié par proximité)
            offsets = [-1] + [i for i in range(1, 8)]
            offsets.sort(key=abs)
            
            for offset in offsets:
                check_date = base_date + timedelta(days=offset)
                if check_date < min_date:
                    continue
                    
                check_date_str = check_date.strftime('%Y-%m-%d')
                found_itineraries = search_itineraries(iata_dep, iata_arr, check_date_str)
                if found_itineraries:
                    best_itin = found_itineraries[0]
                    
                    # Calculer le vrai prix dynamique pour le vol alternatif
                    alt_cap_eco = 0
                    alt_sold_eco = 0
                    
                    # OPTIMISATION : Requête unique (IN) au lieu d'une boucle (N+1)
                    alt_leg_ids = tuple(leg['id_vol'] for leg in best_itin)
                    res_caps = db.session.execute(text("""
                        SELECT a.eco_rang_de, a.eco_rang_a, a.largeur_rangee,
                            COALESCE(SUM(CASE WHEN b.classe = 'Eco' THEN 1 ELSE 0 END), 0) as sold_eco
                        FROM vols v JOIN avions a ON v.immatriculation_avion = a.immatriculation LEFT JOIN billets b ON b.id_vol = v.id_vol
                        WHERE v.id_vol IN :leg_ids GROUP BY v.id_vol, a.immatriculation
                    """), {'leg_ids': alt_leg_ids}).mappings().all()
                    
                    for res in res_caps:
                        def cap(de, a, width): return max(0, a - de + 1) * width if a >= de > 0 else 0
                        alt_cap_eco += cap(res['eco_rang_de'], res['eco_rang_a'], res['largeur_rangee'])
                        alt_sold_eco += int(res['sold_eco'])
                    
                    alt_base_price = sum(float(leg['prix_de_base']) for leg in best_itin)
                    alt_stops = len(best_itin) - 1
                    if alt_stops == 1: alt_base_price *= 0.85
                    elif alt_stops >= 2: alt_base_price *= 0.75
                    if type_vol == 'AR': alt_base_price *= 0.9

                    alt_taux_remplissage = float(alt_sold_eco) / alt_cap_eco if alt_cap_eco > 0 else 0.0
                    
                    p_eco = calculer_prix(alt_base_price, best_itin[0]['date_heure_dep_utc'], datetime.utcnow(), alt_taux_remplissage, alt_taux_remplissage, 'eco')['prix_final']
                    prices = {'eco': max(50, int(p_eco))}
                    
                    alt_has_short = False
                    for i in range(len(best_itin) - 1):
                        laytd = best_itin[i+1]['date_heure_dep_utc'] - best_itin[i]['date_heure_arr_utc']
                        if laytd < timedelta(minutes=60):
                            alt_has_short = True
                    
                    dep_time_local = best_itin[0]['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
                    arr_time_local = best_itin[-1]['date_heure_arr_utc'].replace(tzinfo=timezone.utc).astimezone()
                    
                    alt_stops = len(best_itin) - 1
                    if alt_stops == 0:
                        alt_stops_text = "Vol Direct"
                    elif alt_stops == 1:
                        alt_stops_text = f"1 Escale ({best_itin[0]['id_aeroport_arrivee']})"
                    else:
                        alt_stops_text = f"{alt_stops} Escales"
                        
                    alternative_vols.append({
                        'id_vol': "_".join(str(leg['id_vol']) for leg in best_itin),
                        'date_str': check_date.strftime('%d-%m-%Y'),
                        'date_brute': check_date_str,
                        'prix_eco': prices['eco'],
                        'id_aeroport_depart': best_itin[0]['id_aeroport_depart'],
                        'id_aeroport_arrivee': best_itin[-1]['id_aeroport_arrivee'],
                        'heure_depart_str': dep_time_local.strftime('%H:%M'),
                        'heure_arrivee_str': arr_time_local.strftime('%H:%M'),
                        'is_direct': len(best_itin) == 1,
                        'has_short_layover': alt_has_short,
                        'stops_text': alt_stops_text
                    })
                    
                    if len(alternative_vols) >= 3:
                        break
        except Exception:
            pass
    
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
                           alternative_vols=alternative_vols,
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
                'classe': request.form.get('classe'),
                'classes': request.form.getlist('classes[]'),
                'prix': float(request.form.get('prix', 0)),
                'prix_eco': float(request.form.get('prix_eco', 0)),
                'prix_biz': float(request.form.get('prix_biz', 0)),
                'prix_first': float(request.form.get('prix_first', 0))
            }
            search_params = session.get('search_params', {})
            
            if search_params.get('type_vol') == 'AR':
                session['vol_retour'] = vol_final
            else:
                session['vol_aller'] = vol_final
                
            update_total_panier()
                
        return redirect(url_for('client.booking_passengers'))
                
    # Garde-fou : s'il n'y a pas de vol_aller sélectionné, retour au début
    if 'vol_aller' not in session:
        return redirect(url_for('client.booking'))
        
    return render_template('client/booking_passengers.html')

@client_bp.route('/booking-options', methods=['GET', 'POST'])
@login_required
def booking_options():
    """Options"""
    if 'vol_aller' not in session:
        return redirect(url_for('client.booking'))
        
    if request.method == 'POST':
        session['passagers_data'] = request.form.to_dict()
        session.modified = True
        return redirect(url_for('client.booking_options'))
        
    vol_aller = session.get('vol_aller', {})
    vol_retour = session.get('vol_retour', {})

    def get_leg_info(id_vol_str):
        if not id_vol_str: return []
        legs = str(id_vol_str).split('_')
        leg_data = []
        for idx, leg_id in enumerate(legs):
            if not leg_id: continue
            avion_info = db.session.execute(text("""
                SELECT a.*, v.id_aeroport_depart, v.id_aeroport_arrivee 
                FROM vols v JOIN avions a ON v.immatriculation_avion = a.immatriculation 
                WHERE v.id_vol = :id_vol
            """), {'id_vol': leg_id}).mappings().first()
            
            try:
                taken_seats_rows = db.session.execute(text("SELECT siege FROM billets WHERE id_vol = :id_vol AND siege IS NOT NULL"), {'id_vol': leg_id}).fetchall()
                taken_seats = [r[0] for r in taken_seats_rows if r[0]]
            except Exception:
                db.session.rollback()
                taken_seats = []
                
            if avion_info:
                leg_data.append({'leg_id': leg_id, 'idx': idx, 'avion': dict(avion_info), 'taken_seats': taken_seats, 'dep': avion_info['id_aeroport_depart'], 'arr': avion_info['id_aeroport_arrivee']})
        return leg_data

    aller_legs = get_leg_info(vol_aller.get('id_vol'))
    retour_legs = get_leg_info(vol_retour.get('id_vol'))

    search_params = session.get('search_params', {})
    nb_passagers = int(search_params.get('passagers', 1))
    
    passagers_data = session.get('passagers_data', {})
    classes_aller = vol_aller.get('classes', [vol_aller.get('classe', 'Eco')] * nb_passagers)
    classes_retour = vol_retour.get('classes', [vol_retour.get('classe', 'Eco')] * nb_passagers) if vol_retour else []
        
    passengers = []
    for i in range(1, nb_passagers + 1):
        c_aller = classes_aller[i-1] if (i-1) < len(classes_aller) else 'Eco'
        c_retour = classes_retour[i-1] if classes_retour and (i-1) < len(classes_retour) else c_aller
        passengers.append({
            'index': i - 1, 'num': i,
            'prenom': passagers_data.get(f'prenom_{i}', f'Passager {i}'), 'nom': passagers_data.get(f'nom_{i}', ''),
            'classe_aller': c_aller,
            'classe_retour': c_retour
        })

    return render_template('client/booking_options.html', aller_legs=aller_legs, retour_legs=retour_legs, nb_passagers=nb_passagers, passengers=passengers)

@client_bp.route('/booking-payment', methods=['GET', 'POST'])
@login_required
def booking_payment():
    """Payement"""
    if 'vol_aller' not in session:
        return redirect(url_for('client.booking'))
        
    vol_aller = session.get('vol_aller', {})
    vol_retour = session.get('vol_retour', {})
    legs_aller = str(vol_aller.get('id_vol', '')).split('_') if vol_aller.get('id_vol') else []
    legs_retour = str(vol_retour.get('id_vol', '')).split('_') if vol_retour.get('id_vol') else []

    if request.method == 'POST':
        if 'classe_1' in request.form or 'bagages_1' in request.form:
            search_params = session.get('search_params', {})
            nb_passagers = int(search_params.get('passagers', 1))
            
            prix_options = 0
            options_per_passager = []
            new_classes_aller = []
            new_classes_retour = []
            total_aller_price = 0
            total_retour_price = 0
            
            for i in range(1, nb_passagers + 1):
                bag = request.form.get(f'bagages_{i}', '0')
                rep = request.form.get(f'repas_{i}', 'standard')
                p_class_aller = request.form.get(f'classe_aller_{i}', 'Eco')
                p_class_retour = request.form.get(f'classe_retour_{i}', 'Eco')
                new_classes_aller.append(p_class_aller)
                new_classes_retour.append(p_class_retour)
                
                sieges_aller = []
                for idx_leg in range(len(legs_aller)):
                    s = request.form.get(f'siege_aller_{idx_leg}_{i}')
                    if s: sieges_aller.append(s)

                sieges_retour = []
                for idx_leg in range(len(legs_retour)):
                    s = request.form.get(f'siege_retour_{idx_leg}_{i}')
                    if s: sieges_retour.append(s)
                
                if p_class_aller == 'Eco': 
                    total_aller_price += vol_aller.get('prix_eco', 0)
                elif p_class_aller == 'Business': 
                    total_aller_price += vol_aller.get('prix_biz', 0)
                elif p_class_aller == 'First': 
                    total_aller_price += vol_aller.get('prix_first', 0)
                    
                if p_class_retour == 'Eco':
                    total_retour_price += vol_retour.get('prix_eco', 0)
                elif p_class_retour == 'Business':
                    total_retour_price += vol_retour.get('prix_biz', 0)
                elif p_class_retour == 'First':
                    total_retour_price += vol_retour.get('prix_first', 0)
                
                def rank(c): return {'Eco':1, 'Business':2, 'First':3}.get(c, 1)
                max_rank = max(rank(p_class_aller), rank(p_class_retour) if vol_retour else 1)
                highest_class = 'First' if max_rank == 3 else 'Business' if max_rank == 2 else 'Eco'
                
                if highest_class == 'Eco':
                    prix_options += TARIFS_OPTIONS['bagages_eco'].get(bag, 0)
                    prix_options += TARIFS_OPTIONS['repas_eco'].get(rep, 0)
                elif highest_class == 'Business':
                    bag = '2_23kg'
                    if rep not in ['premium', 'vegetarien']: rep = 'premium'
                elif highest_class == 'First':
                    bag = '2_32kg'
                    if rep not in ['gastronomique', 'vegetarien']: rep = 'gastronomique'
                
                options_per_passager.append({'bagages': bag, 'repas': rep, 'classe_aller': p_class_aller, 'classe_retour': p_class_retour, 'sieges_aller': sieges_aller, 'sieges_retour': sieges_retour})
            
            # Mise à jour du cache de session pour le vol et le prix
            if 'vol_aller' in session:
                session['vol_aller']['classes'] = new_classes_aller
                session['vol_aller']['prix'] = total_aller_price / nb_passagers if nb_passagers > 0 else 0
            if 'vol_retour' in session:
                session['vol_retour']['classes'] = new_classes_retour
                session['vol_retour']['prix'] = total_retour_price / nb_passagers if nb_passagers > 0 else 0

            session['options'] = {
                'passagers': options_per_passager,
                'prix': prix_options / nb_passagers if nb_passagers > 0 else 0
            }
            update_total_panier()
            session.modified = True
            return redirect(url_for('client.booking_payment'))
        else:
            # --- LOGIQUE FINALE : INSERTION BASE DE DONNÉES EN CASCADE ---
            try:
                import string, random
                # Génération d'un PNR unique de 6 caractères (Alphanumérique)
                pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                
                # 1. Création du Master "Réservation"
                db.session.execute(text("""
                    INSERT INTO reservations (id_client, date_reservation, statut, pnr)
                    VALUES (:id_client, :date_res, 'Confirmée', :pnr)
                """), {
                    'id_client': session.get('user_id'),
                    'date_res': datetime.utcnow(),
                    'pnr': pnr
                })
                
                # Récupération de l'ID généré pour la réservation
                id_reservation = db.session.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                
                # 2. Création des Billets (Multi-passagers & Multi-segments)
                options = session.get('options', {}).get('passagers', [])
                passagers_data = session.get('passagers_data', {})
                
                for i, p_opt in enumerate(options):
                    num = i + 1
                    prenom = passagers_data.get(f'prenom_{num}', 'Inconnu')
                    nom = passagers_data.get(f'nom_{num}', 'Inconnu')
                    
                    for idx_leg, leg in enumerate(legs_aller):
                        if leg:
                            siege_assigne = p_opt.get('sieges_aller', [])[idx_leg] if idx_leg < len(p_opt.get('sieges_aller', [])) else None
                            
                            db.session.execute(text("""
                                INSERT INTO billets (id_reservation, id_vol, prenom_passager, nom_passager, classe, siege, bagages, repas)
                                VALUES (:id_res, :id_vol, :prenom, :nom, :classe, :siege, :bagages, :repas)
                            """), {
                                'id_res': id_reservation,
                                'id_vol': leg,
                                'prenom': prenom,
                                'nom': nom,
                                'classe': p_opt.get('classe_aller', 'Eco'),
                                'siege': siege_assigne,
                                'bagages': p_opt.get('bagages', '0'),
                                'repas': p_opt.get('repas', 'standard')
                            })
                            
                    for idx_leg, leg in enumerate(legs_retour):
                        if leg:
                            siege_assigne = p_opt.get('sieges_retour', [])[idx_leg] if idx_leg < len(p_opt.get('sieges_retour', [])) else None
                            
                            db.session.execute(text("""
                                INSERT INTO billets (id_reservation, id_vol, prenom_passager, nom_passager, classe, siege, bagages, repas)
                                VALUES (:id_res, :id_vol, :prenom, :nom, :classe, :siege, :bagages, :repas)
                            """), {
                                'id_res': id_reservation,
                                'id_vol': leg,
                                'prenom': prenom,
                                'nom': nom,
                                'classe': p_opt.get('classe_retour', 'Eco'),
                                'siege': siege_assigne,
                                'bagages': p_opt.get('bagages', '0'),
                                'repas': p_opt.get('repas', 'standard')
                            })
                
                db.session.commit()
                flash(f'Paiement réussi ! Votre réservation (PNR: {pnr}) est confirmée.', 'success')
                
                # Nettoyage du cache
                for key in ['search_params', 'vol_aller', 'vol_retour', 'options', 'passagers_data', 'total_panier']:
                    session.pop(key, None)
                    
                return redirect(url_for('client.mes_reservations'))
                
            except Exception as e:
                db.session.rollback()
                print(f"Erreur d'insertion BDD: {e}")
                flash("Une erreur s'est produite lors de l'émission de vos billets.", 'danger')
                return redirect(url_for('client.booking_payment'))
        
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