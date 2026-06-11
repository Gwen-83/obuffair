"""
Routes client : recherche vols, détail vol, panier, checkout, historique réservations.
Gère le profil, modifications de réservation et gestion de compte.
"""

from functools import wraps
from flask import Blueprint, render_template, request, session, url_for, redirect, flash, current_app, make_response, jsonify
from app import db
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from app.model import Aeroport, Vols, User, Support, Reservation, Passager, Billet
from datetime import datetime, timedelta, timezone
from app.algos.search import search_itineraries
from app.algos.yield_management import calculer_prix
from app.algos.booking import (
    TARIFS_OPTIONS, sync_loyalty_points, 
    create_reservation_in_db, update_reservation_in_db, 
    group_flights_by_journey
)
import string, random
import re
import os
import requests
import json
from werkzeug.utils import secure_filename
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


# Blueprint
client_bp = Blueprint('client', __name__)

_airport_offsets_cache = {}
def get_local_time(dt_utc, iata_code):
    if not _airport_offsets_cache:
        try:
            rows = db.session.execute(text("SELECT id_aeroport, decalage_utc FROM aeroports")).fetchall()
            for r in rows: _airport_offsets_cache[r[0]] = r[1]
        except Exception: pass
    offset = _airport_offsets_cache.get(iata_code, "+00:00")
    try:
        sign = 1 if offset[0] == '+' else -1
        h, m = int(offset[1:3]), int(offset[4:6]) if len(offset) > 4 else 0
        return dt_utc + timedelta(hours=sign*h, minutes=sign*m)
    except Exception: return dt_utc

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

def clear_booking_session(keep_search_params=False):
    keys = ['vol_aller', 'vol_retour', 'options', 'passagers_data', 'total_panier', 'modifying_pnr', 'original_total', 'highlight_option']
    if not keep_search_params:
        keys.append('search_params')
    for k in keys:
        session.pop(k, None)
    session.modified = True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Veuillez vous connecter pour accéder à la réservation.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@client_bp.after_request
def disable_booking_cache(response):
    """Désactiver la mise en cache (BFCache) pour le flux de réservation."""
    if request.endpoint and request.endpoint.startswith('client.booking'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@client_bp.route('/')
def accueil():
    """Accueil"""
    if session.get('modifying_pnr'):
        clear_booking_session()
    
    # --- Liste des aéroports pour l'animation de recherche ---
    try:
        aeroports_db = db.session.execute(text("SELECT id_aeroport, ville, latitude, longitude FROM aeroports")).mappings().all()
        airports_data = []
        for a in aeroports_db:
            airports_data.append({
                'iata': a['id_aeroport'],
                'city': a['ville'],
                'lat': float(a['latitude']) if a['latitude'] is not None else None,
                'lng': float(a['longitude']) if a['longitude'] is not None else None
            })
    except Exception as e:
        print(f"Erreur SQL Aéroports: {e}")
        airports_data = []

    # --- Requête pour toutes les routes (Carte Réseau) ---
    try:
        routes_db = db.session.execute(text("""
            SELECT DISTINCT 
                ad.id_aeroport as dep_iata, ad.latitude as dep_lat, ad.longitude as dep_lng,
                aa.id_aeroport as arr_iata, aa.latitude as arr_lat, aa.longitude as arr_lng
            FROM vols v
            JOIN aeroports ad ON v.id_aeroport_depart = ad.id_aeroport
            JOIN aeroports aa ON v.id_aeroport_arrivee = aa.id_aeroport
            WHERE ad.latitude IS NOT NULL AND ad.longitude IS NOT NULL
              AND aa.latitude IS NOT NULL AND aa.longitude IS NOT NULL
        """)).mappings().all()
        
        map_routes = [{
            'dep_iata': r['dep_iata'], 'dep_lat': float(r['dep_lat']), 'dep_lng': float(r['dep_lng']), 
            'arr_iata': r['arr_iata'], 'arr_lat': float(r['arr_lat']), 'arr_lng': float(r['arr_lng'])
        } for r in routes_db]
    except Exception as e:
        print(f"Erreur SQL Carte Routes: {e}")
        map_routes = []

    # --- Requête pour les destinations du carrousel ---
    try:
        lowest_prices_query = db.session.query(
            Aeroport.id_aeroport,
            Aeroport.ville,
            Aeroport.latitude,
            Aeroport.longitude,
            func.min(Vols.prix_de_base).label('min_prix')
        ).join(Vols, Vols.id_aeroport_arrivee == Aeroport.id_aeroport)\
         .filter(Vols.date_heure_dep_utc > datetime.utcnow())\
         .group_by(Aeroport.id_aeroport, Aeroport.ville, Aeroport.latitude, Aeroport.longitude)\
         .order_by(func.min(Vols.prix_de_base)).limit(10).all()
         
        map_destinations = []
        for row in lowest_prices_query:
            if row.latitude is not None and row.longitude is not None:
                map_destinations.append({
                    'iata': row.id_aeroport,
                    'ville': row.ville,
                    'lat': float(row.latitude),
                    'lng': float(row.longitude),
                    'prix': int(row.min_prix) if row.min_prix is not None else 0
                })

        
        destinations = []
        troll_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS4u61wav4I9SolemD3pFQHW0iKL8X1ReekEg&s"
        
        current_time = datetime.utcnow().timestamp()
        last_troll_time = session.get('last_troll_time', 0)
        show_troll = False
        
        # Apparition limitée : au hasard toutes les 3 à 5 minutes (180 à 300 sec)
        if (current_time - last_troll_time) > random.randint(180, 300):
            show_troll = True
            session['last_troll_time'] = current_time

        # --- GESTION DU CACHE D'IMAGES UNSPLASH (PERSISTANT) ---
        cache_file_path = os.path.join(current_app.instance_path, 'unsplash_cache.json')
        
        # Initialisation du cache en mémoire s'il n'existe pas
        if 'UNSPLASH_CACHE' not in current_app.config:
            try:
                # 1. Essayer de charger depuis le fichier
                with open(cache_file_path, 'r') as f:
                    current_app.config['UNSPLASH_CACHE'] = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # 2. Si le fichier n'existe pas ou est corrompu, on crée le cache de base
                current_app.config['UNSPLASH_CACHE'] = {
                    'Rome': 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=600&auto=format&fit=crop',
                    'Londres': 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?q=80&w=600&auto=format&fit=crop',
                    'Madrid': 'https://images.unsplash.com/photo-1543783207-ec64e4d95325?q=80&w=600&auto=format&fit=crop',
                    'Berlin': 'https://images.unsplash.com/photo-1560969184-10fe8719e047?q=80&w=600&auto=format&fit=crop',
                    'Paris': 'https://images.unsplash.com/photo-1499856871958-5b9627545d1a?q=80&w=600&auto=format&fit=crop',
                    'Amsterdam': 'https://images.unsplash.com/photo-1517736996303-4eec4a66bb17?q=80&w=600&auto=format&fit=crop'
                }
                # Et on le sauvegarde pour la prochaine fois
                try:
                    os.makedirs(current_app.instance_path, exist_ok=True)
                    with open(cache_file_path, 'w') as f:
                        json.dump(current_app.config['UNSPLASH_CACHE'], f, indent=4)
                except IOError as e:
                    print(f"Erreur lors de la sauvegarde du cache initial : {e}")
            
        for row in lowest_prices_query:
            # 1. Vérifie si l'image de la ville est déjà dans le cache
            if row.ville in current_app.config['UNSPLASH_CACHE']:
                base_url = current_app.config['UNSPLASH_CACHE'][row.ville]
            else:
                base_url = None
                # 2. Si non, appel à l'API Unsplash
                unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY')
                if unsplash_key:
                    try:
                        params = {'query': f"{row.ville} city landmark", 'client_id': unsplash_key, 'per_page': 1, 'orientation': 'portrait'}
                        resp = requests.get("https://api.unsplash.com/search/photos", params=params, timeout=2)
                        if resp.status_code == 200 and resp.json().get('results'):
                            base_url = resp.json()['results'][0]['urls']['small']
                    except Exception as e:
                        print(f"Erreur API Unsplash pour {row.ville}: {e}")
                # 3. Fallback en cas d'erreur
                if not base_url:
                    base_url = 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=600&auto=format&fit=crop'
                
                # 4. Sauvegarde la nouvelle image dans le cache (mémoire ET fichier)
                current_app.config['UNSPLASH_CACHE'][row.ville] = base_url
                try:
                    with open(cache_file_path, 'w') as f:
                        json.dump(current_app.config['UNSPLASH_CACHE'], f, indent=4)
                except IOError as e:
                    print(f"Erreur lors de la mise à jour du fichier cache : {e}")
                
            destinations.append({
                'ville': row.ville, 
                'prix': int(row.min_prix) if row.min_prix is not None else 0,
                'image_url': base_url
            })
            
        # Si les conditions de temps sont réunies, on remplace UNE image au hasard par le troll
        if show_troll and destinations:
            random_idx = random.randint(0, len(destinations) - 1)
            destinations[random_idx]['image_url'] = troll_url
    except Exception as e:
        print(f"Erreur SQL Carrousel Destinations: {e}")
        destinations = []
    
    # Fallback si aucun vol n'est présent dans la BDD ou en cas d'erreur
    if not destinations:
        destinations = [
            {'ville': 'Rome', 'prix': 124, 'image_url': 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=600&auto=format&fit=crop'},
            {'ville': 'Londres', 'prix': 98, 'image_url': 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?q=80&w=600&auto=format&fit=crop'},
            {'ville': 'Madrid', 'prix': 85, 'image_url': 'https://images.unsplash.com/photo-1543783207-ec64e4d95325?q=80&w=600&auto=format&fit=crop'},
            {'ville': 'Berlin', 'prix': 110, 'image_url': 'https://images.unsplash.com/photo-1560969184-10fe8719e047?q=80&w=600&auto=format&fit=crop'}
        ]

    loyalty_info = None
    next_flight = None
    prochains_vols_data = []
    user_id = session.get('user_id')
    
    if user_id:
        client_connecte = db.session.get(User, user_id)
        if client_connecte:
            sync_loyalty_points(client_connecte)
            loyalty_info = {
                'status': client_connecte.infos_fidelite['actuel'],
                'points': client_connecte.points_fidelite,
                'progress_percent': int((client_connecte.infos_fidelite['accumules'] / client_connecte.infos_fidelite['points_max']) * 100) if client_connecte.infos_fidelite['points_max'] > 0 else 100,
                'points_to_next': client_connecte.infos_fidelite['restant'],
                'next_tier': client_connecte.infos_fidelite['suivant'],
                'flights_year': client_connecte.reservations.filter_by(statut='Confirmee').count()
            }
            
            prochains_billets = client_connecte.get_prochains_vols()
            vols_vus = set()
            now_minus_2h = datetime.utcnow() - timedelta(hours=2)
            
            if prochains_billets:
                for billet in prochains_billets:
                    vol = billet.vol
                    if vol.date_heure_dep_utc < now_minus_2h:
                        continue
                        
                    resa = billet.reservation
                    unique_key = f"{resa.id_reservation}_{vol.id_vol}"
                    if unique_key in vols_vus:
                        continue
                    vols_vus.add(unique_key)
                    
                    nb_passagers = sum(1 for b in resa.billets if b.id_vol == vol.id_vol)
                    dep_time_local = get_local_time(vol.date_heure_dep_utc, vol.id_aeroport_depart)
                    arr_time_local = get_local_time(vol.date_heure_arr_utc, vol.id_aeroport_arrivee)
                    
                    prochains_vols_data.append({
                        'id_reservation': resa.id_reservation,
                        'flight_number': f"OB{vol.id_vol}",
                        'date': dep_time_local.strftime('%d/%m/%Y'),
                        'status_text': "À l'heure" if vol.statut.lower() == "à l'heure" else vol.statut.capitalize(),
                        'status_class': "status-ontime" if vol.statut.lower() == "à l'heure" else "status-delayed",
                        'dep_iata': vol.id_aeroport_depart,
                        'dep_city': vol.aeroport_depart.ville if vol.aeroport_depart else '',
                        'nb_passagers': nb_passagers,
                        'arr_iata': vol.id_aeroport_arrivee,
                        'arr_city': vol.aeroport_arrivee.ville if vol.aeroport_arrivee else '',
                        'dep_time': dep_time_local.strftime('%H:%M'),
                        'arr_time': arr_time_local.strftime('%H:%M'),
                        'pnr': resa.pnr or "En attente"
                    })
                    
                    if len(prochains_vols_data) >= 3:
                        break

    return render_template('client/acceuil.html', destinations=destinations, loyalty_info=loyalty_info, prochains_vols=prochains_vols_data, airports_data=airports_data, map_routes=map_routes)

@client_bp.route('/profil', methods=['GET', 'POST'])
def profil():
    """Profil"""
    if session.get('modifying_pnr'):
        clear_booking_session()
        
    user_id = session.get('user_id')
    
    # Si l'utilisateur n'est pas connecté, on le redirige
    if not user_id:
        return redirect(url_for('client.accueil'))
        
    # Récupération du client en base de données
    client_connecte = db.session.get(User, user_id)
    if not client_connecte:
        return redirect(url_for('client.accueil'))
        
    # Synchronisation silencieuse à l'ouverture du profil
    sync_loyalty_points(client_connecte)
        
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
            
        # Suppression des documents si demandée
        if request.form.get('delete_doc_1') == '1':
            client_connecte.document_identite = None
        if request.form.get('delete_doc_2') == '1':
            client_connecte.document_identite_2 = None

        # Traitement du fichier uploadé
        if 'document_file' in request.files:
            file = request.files['document_file']
            if file and file.filename != '':
                # Sécurisation du nom de fichier et ajout d'un préfixe unique avec l'ID du client
                filename = secure_filename(file.filename)
                unique_filename = f"user_{client_connecte.id_client}_{filename}"
                
                # Créer le dossier s'il n'existe pas
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'documents')
                os.makedirs(upload_folder, exist_ok=True)
                
                filepath = os.path.join(upload_folder, unique_filename)
                file.save(filepath)
                client_connecte.document_identite = unique_filename
                
        # Traitement du 2ème fichier uploadé
        if 'document_file_2' in request.files:
            file2 = request.files['document_file_2']
            if file2 and file2.filename != '':
                filename2 = secure_filename(file2.filename)
                unique_filename2 = f"user_{client_connecte.id_client}_2_{filename2}"
                
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'documents')
                os.makedirs(upload_folder, exist_ok=True)
                
                filepath = os.path.join(upload_folder, unique_filename2)
                file2.save(filepath)
                client_connecte.document_identite_2 = unique_filename2

        db.session.commit()
        session['prenom'] = client_connecte.prenom
        session['nom'] = client_connecte.nom
        flash('Vos informations ont été mises à jour avec succès.', 'success')
        return redirect(url_for('client.profil'))
        
    prochains_billets = client_connecte.get_prochains_vols()
    prochains_vols_data = []
    vols_vus = set()  # Pour éviter d'afficher le même vol X fois si X passagers
    
    now_minus_2h = datetime.utcnow() - timedelta(hours=2)
    
    if prochains_billets:
        for billet in prochains_billets:
            vol = billet.vol
            if vol.date_heure_dep_utc < now_minus_2h:
                continue
                
            resa = billet.reservation
            
            # Clé unique pour regrouper par réservation ET par vol (pour les escales)
            unique_key = f"{resa.id_reservation}_{vol.id_vol}"
            if unique_key in vols_vus:
                continue
            vols_vus.add(unique_key)
            
            # Calcul du nombre de passagers rattachés à cette réservation pour ce vol
            nb_passagers = sum(1 for b in resa.billets if b.id_vol == vol.id_vol)

            dep_time_local = get_local_time(vol.date_heure_dep_utc, vol.id_aeroport_depart)
            arr_time_local = get_local_time(vol.date_heure_arr_utc, vol.id_aeroport_arrivee)

            date_vol = dep_time_local.strftime('%d/%m/%Y')
            
            status_text = "À l'heure" if vol.statut.lower() == "à l'heure" else vol.statut.capitalize()
            status_class = "status-ontime" if vol.statut.lower() == "à l'heure" else "status-delayed"
            
            prochains_vols_data.append({
                'id_reservation': resa.id_reservation,
                'flight_number': f"OB{vol.id_vol}",
                'date': date_vol,
                'status_text': status_text,
                'status_class': status_class,
                'dep_iata': vol.id_aeroport_depart,
                'dep_city': vol.aeroport_depart.ville if vol.aeroport_depart else '',
                'nb_passagers': nb_passagers,
                'arr_iata': vol.id_aeroport_arrivee,
                'arr_city': vol.aeroport_arrivee.ville if vol.aeroport_arrivee else '',
                'dep_time': dep_time_local.strftime('%H:%M'),
                'arr_time': arr_time_local.strftime('%H:%M'),
                'pnr': resa.pnr or "En attente"
            })
            
            # Limiter à l'affichage des 3 prochains vols
            if len(prochains_vols_data) >= 3:
                break
            
    return render_template('client/profil.html', client=client_connecte, prochains_vols=prochains_vols_data)

@client_bp.route('/support', methods=['GET', 'POST'])
def support():
    """Formulaire de ticket de support client"""
    if session.get('modifying_pnr'):
        clear_booking_session()
        
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

@client_bp.route('/api/available-dates', methods=['GET'])
def available_dates():
    """Renvoie les dates disponibles (jusqu'à 2 escales) pour un aller et un retour."""
    depart = request.args.get('depart')
    arrivee = request.args.get('arrivee')
    
    if not depart or not arrivee:
        return jsonify({'aller': [], 'retour': []})
        
    def get_dates_for_route(dep, arr):
        valid_dates = set()
        now_bound = datetime.utcnow() + timedelta(hours=2)
        
        # 1. Vols directs
        direct_flights = db.session.execute(text("""
            SELECT * FROM vols 
            WHERE id_aeroport_depart = :origin AND id_aeroport_arrivee = :destination
            AND date_heure_dep_utc >= :now_bound
        """), {'origin': dep, 'destination': arr, 'now_bound': now_bound}).mappings().all()
        
        for f in direct_flights:
            f_local = get_local_time(f['date_heure_dep_utc'], f['id_aeroport_depart'])
            valid_dates.add(f_local.strftime('%Y-%m-%d'))
            
        # 2. Vols avec 1 Escale
        first_legs = db.session.execute(text("""
            SELECT * FROM vols 
            WHERE id_aeroport_depart = :origin AND id_aeroport_arrivee != :destination
            AND date_heure_dep_utc >= :now_bound
        """), {'origin': dep, 'destination': arr, 'now_bound': now_bound}).mappings().all()
        
        if first_legs:
            min_global_dep = min(leg['date_heure_arr_utc'] + timedelta(minutes=40) for leg in first_legs)
            max_global_dep = max(leg['date_heure_arr_utc'] + timedelta(hours=12) for leg in first_legs)
            
            arrival_airports = list(set(leg['id_aeroport_arrivee'] for leg in first_legs))
            in_clause = ', '.join(f"'{iata}'" for iata in arrival_airports)
            
            second_legs_all = db.session.execute(text(f"""
                SELECT * FROM vols 
                WHERE id_aeroport_depart IN ({in_clause})
                AND date_heure_dep_utc >= :min_dep AND date_heure_dep_utc <= :max_dep
            """), {'min_dep': min_global_dep, 'max_dep': max_global_dep}).mappings().all()
            
            potential_two_stops = []
            for leg1 in first_legs:
                min_dep = leg1['date_heure_arr_utc'] + timedelta(minutes=40)
                max_dep = leg1['date_heure_arr_utc'] + timedelta(hours=12)
                for leg2 in second_legs_all:
                    if leg2['id_aeroport_depart'] == leg1['id_aeroport_arrivee'] and min_dep <= leg2['date_heure_dep_utc'] <= max_dep:
                        if leg2['id_aeroport_arrivee'] == dep: continue
                        if leg2['id_aeroport_arrivee'] == arr:
                            f_local = get_local_time(leg1['date_heure_dep_utc'], leg1['id_aeroport_depart'])
                            valid_dates.add(f_local.strftime('%Y-%m-%d'))
                        else:
                            potential_two_stops.append((leg1, leg2))
            
            # 3. Vols avec 2 Escales
            if potential_two_stops:
                min_global_dep_3 = min(leg2['date_heure_arr_utc'] + timedelta(minutes=40) for _, leg2 in potential_two_stops)
                max_global_dep_3 = max(leg2['date_heure_arr_utc'] + timedelta(hours=12) for _, leg2 in potential_two_stops)
                arrival_airports_2 = list(set(leg2['id_aeroport_arrivee'] for _, leg2 in potential_two_stops))
                in_clause_2 = ', '.join(f"'{iata}'" for iata in arrival_airports_2)
                
                third_legs_all = db.session.execute(text(f"""
                    SELECT * FROM vols 
                    WHERE id_aeroport_depart IN ({in_clause_2})
                    AND id_aeroport_arrivee = :destination
                    AND date_heure_dep_utc >= :min_dep AND date_heure_dep_utc <= :max_dep
                """), {'destination': arr, 'min_dep': min_global_dep_3, 'max_dep': max_global_dep_3}).mappings().all()
                
                for leg1, leg2 in potential_two_stops:
                    min_dep_3 = leg2['date_heure_arr_utc'] + timedelta(minutes=40)
                    max_dep_3 = leg2['date_heure_arr_utc'] + timedelta(hours=12)
                    for leg3 in third_legs_all:
                        if leg3['id_aeroport_depart'] == leg2['id_aeroport_arrivee'] and min_dep_3 <= leg3['date_heure_dep_utc'] <= max_dep_3:
                            f_local = get_local_time(leg1['date_heure_dep_utc'], leg1['id_aeroport_depart'])
                            valid_dates.add(f_local.strftime('%Y-%m-%d'))

        return sorted(list(valid_dates))

    try:
        return jsonify({
            'aller': get_dates_for_route(depart, arrivee),
            'retour': get_dates_for_route(arrivee, depart)
        })
    except Exception as e:
        print(f"Error fetching available dates: {e}")
        return jsonify({'aller': [], 'retour': []})

@client_bp.route('/booking')
@login_required
def booking():
    """Réservation"""
    if session.get('modifying_pnr'):
        clear_booking_session()
    elif 'vol_aller' in session:
        clear_booking_session(keep_search_params=True)
        
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
                'classes': request.form.getlist('classes[]') or [request.form.get('classe', 'Eco')] * int(session.get('search_params', {}).get('passagers', 1)),
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

        # Conversion des heures extrêmes en heure locale
        dep_time_local = get_local_time(legs[0]['date_heure_dep_utc'], legs[0]['id_aeroport_depart'])
        arr_time_local = get_local_time(legs[-1]['date_heure_arr_utc'], legs[-1]['id_aeroport_arrivee'])
        
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
            leg_dep_local = get_local_time(leg['date_heure_dep_utc'], leg['id_aeroport_depart'])
            leg_arr_local = get_local_time(leg['date_heure_arr_utc'], leg['id_aeroport_arrivee'])
            
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
                    
                    dep_time_local = get_local_time(best_itin[0]['date_heure_dep_utc'], best_itin[0]['id_aeroport_depart'])
                    arr_time_local = get_local_time(best_itin[-1]['date_heure_arr_utc'], best_itin[-1]['id_aeroport_arrivee'])
                    
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
                           titre=titre,
                           highlight_option=session.pop('highlight_option', None))

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
                'classes': request.form.getlist('classes[]') or [request.form.get('classe', 'Eco')] * int(session.get('search_params', {}).get('passagers', 1)),
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
    modifying_pnr = session.get('modifying_pnr')

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
                if modifying_pnr:
                    taken_seats_rows = db.session.execute(text("""
                        SELECT b.siege FROM billets b 
                        JOIN reservations r ON b.id_reservation = r.id_reservation 
                        WHERE b.id_vol = :id_vol AND b.siege IS NOT NULL AND r.pnr != :pnr AND r.statut != 'Annulee'
                    """), {'id_vol': leg_id, 'pnr': modifying_pnr}).fetchall()
                else:
                    taken_seats_rows = db.session.execute(text("""
                        SELECT b.siege FROM billets b 
                        JOIN reservations r ON b.id_reservation = r.id_reservation 
                        WHERE b.id_vol = :id_vol AND b.siege IS NOT NULL AND r.statut != 'Annulee'
                    """), {'id_vol': leg_id}).fetchall()
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
    options_data = session.get('options', {}).get('passagers', [])
    
    classes_aller = vol_aller.get('classes')
    if not classes_aller:
        classes_aller = [vol_aller.get('classe', 'Eco')] * nb_passagers
        
    classes_retour = vol_retour.get('classes') if vol_retour else []
    if vol_retour and not classes_retour:
        classes_retour = [vol_retour.get('classe', 'Eco')] * nb_passagers
        
    passengers = []
    for i in range(1, nb_passagers + 1):
        c_aller = classes_aller[i-1] if (i-1) < len(classes_aller) else 'Eco'
        c_retour = classes_retour[i-1] if classes_retour and (i-1) < len(classes_retour) else c_aller
        p_opt = options_data[i-1] if i-1 < len(options_data) else {}
        passengers.append({
            'index': i - 1, 'num': i,
            'prenom': passagers_data.get(f'prenom_{i}', f'Passager {i}'), 'nom': passagers_data.get(f'nom_{i}', ''),
            'classe_aller': c_aller,
            'classe_retour': c_retour,
            'sieges_aller': p_opt.get('sieges_aller', []),
            'sieges_retour': p_opt.get('sieges_retour', []),
            'repas': p_opt.get('repas', 'standard'),
            'bagages': p_opt.get('bagages', '0')
        })

    return render_template('client/booking_options.html', aller_legs=aller_legs, retour_legs=retour_legs, nb_passagers=nb_passagers, passengers=passengers, highlight_option=session.pop('highlight_option', None))

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
                    prix_options += TARIFS_OPTIONS['bagages_eco'].get(bag, 0)
                    bag_qty = int(bag) if str(bag).isdigit() else 0
                    bag = f"{bag_qty + 2}_23kg"
                    if rep not in ['premium', 'vegetarien']: rep = 'premium'
                elif highest_class == 'First':
                    prix_options += TARIFS_OPTIONS['bagages_eco'].get(bag, 0)
                    bag_qty = int(bag) if str(bag).isdigit() else 0
                    bag = f"{bag_qty + 2}_32kg"
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
            # --- LOGIQUE FINALE : INSERTION BASE DE DONNÉES ---
            modifying_pnr = session.get('modifying_pnr')
            if modifying_pnr:
                reservation_id, error_msg = update_reservation_in_db(session, modifying_pnr)
            else:
                reservation_id, error_msg = create_reservation_in_db(session)
            
            if reservation_id:
                reservation = db.session.get(Reservation, reservation_id)
                
                # Calcul uniquement pour l'affichage visuel (les vrais points sont ajoutés via sync_loyalty_points)
                cart_total = float(session.get('total_panier', 0))
                if modifying_pnr:
                    diff = cart_total - float(session.get('original_total', 0))
                    pts_gagnes = int(diff * 10) if diff > 0 else 0
                else:
                    pts_gagnes = int(cart_total * 10)
                    
                if pts_gagnes > 0:
                    flash(f'Paiement réussi ! Réservation confirmée. Vous venez de gagner {pts_gagnes} Miles !', 'success')
                else:
                    flash(f'Paiement réussi ! Votre réservation (PNR: {reservation.pnr}) est confirmée.', 'success')
                
                # Nettoyage du cache
                for key in ['search_params', 'vol_aller', 'vol_retour', 'options', 'passagers_data', 'total_panier', 'modifying_pnr', 'original_total']:
                    session.pop(key, None)
                
                return redirect(url_for('client.booking_confirmation', reservation_id=reservation_id))
            else:
                session['booking_error'] = error_msg
                return redirect(url_for('client.booking_confirmation', reservation_id='error'))
        
    # --- RÉCUPÉRATION DES DÉTAILS D'ESCALES POUR L'AFFICHAGE ---
    def get_leg_info(id_vol_str):
        if not id_vol_str: return []
        legs = [l for l in str(id_vol_str).split('_') if l]
        if not legs: return []
        
        vol_info_rows = db.session.execute(text("""
            SELECT id_vol, id_aeroport_depart, id_aeroport_arrivee 
            FROM vols WHERE id_vol IN :leg_ids
        """), {'leg_ids': tuple(legs)}).mappings().all()
        
        vols_map = {str(r['id_vol']): r for r in vol_info_rows}
        
        leg_data = []
        for leg_id in legs:
            vol_info = vols_map.get(leg_id)
            if vol_info:
                leg_data.append({'dep': vol_info['id_aeroport_depart'], 'arr': vol_info['id_aeroport_arrivee']})
        return leg_data

    aller_legs = get_leg_info(vol_aller.get('id_vol'))
    retour_legs = get_leg_info(vol_retour.get('id_vol'))

    return render_template('client/booking_payment.html', aller_legs=aller_legs, retour_legs=retour_legs)

@client_bp.route('/booking-confirmation/<reservation_id>')
@login_required
def booking_confirmation(reservation_id):
    if reservation_id == 'error':
        error_msg = session.get('booking_error', 'Erreur SQL ou technique inconnue.')
        session.pop('booking_error', None)
        return render_template('client/booking_confirmation.html', error=error_msg)
        
    try:
        res_id = int(reservation_id)
    except ValueError:
        return redirect(url_for('client.booking'))
        
    # Sécurise l'accès : seul le client qui a fait la résa peut la voir
    reservation = db.session.query(Reservation).filter_by(id_reservation=res_id, id_client=session['user_id']).first_or_404()
    return render_template('client/booking_confirmation.html', reservation=reservation)

@client_bp.route('/download-ticket/<int:reservation_id>')
@login_required
def download_ticket(reservation_id):
    reservation = db.session.query(Reservation).filter_by(id_reservation=reservation_id, id_client=session['user_id']).first_or_404()
    
    html_content = render_template('client/ticket_pdf.html', reservation=reservation)

    if not WEASYPRINT_AVAILABLE:
        # Fallback natif : on renvoie le HTML pour que le navigateur génère le PDF lui-même
        return html_content
        
    try:
        pdf_file = HTML(string=html_content).write_pdf()
        response = make_response(pdf_file)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Obuffair_Ticket_{reservation.pnr}.pdf'
        return response
    except Exception as e:
        # Si WeasyPrint crashe à l'exécution (ex: librairies C défectueuses sur Mac), on utilise le fallback
        return html_content

@client_bp.route('/mes-reservations', methods=['GET', 'POST'])
@login_required
def mes_reservations():
    """Mes réservations"""
    if session.get('modifying_pnr') or session.get('search_params'):
        clear_booking_session()
        
    user_id = session.get('user_id')
    
    # Récupérer les réservations de l'utilisateur
    user_reservations = db.session.query(Reservation).options(
        joinedload(Reservation.billets).joinedload(Billet.vol).joinedload(Vols.aeroport_depart),
        joinedload(Reservation.billets).joinedload(Billet.vol).joinedload(Vols.aeroport_arrivee),
        joinedload(Reservation.billets).joinedload(Billet.passager)
    ).filter_by(id_client=user_id).order_by(Reservation.date_reservation.desc()).all()
    
    reservations_data = []
    
    # Dictionnaire pour mapper les options de repas
    repas_map = {0: 'Standard', 1: 'Premium', 2: 'Végétarien', 3: 'Gastronomique'}
    
    for resa in user_reservations:
        aller_vols_obj, _ = group_flights_by_journey(resa.billets)
        aller_ids = {v.id_vol for v in aller_vols_obj}

        resa_dict = {
            'id_reservation': resa.id_reservation,
            'pnr': resa.pnr or 'N/A',
            'date_resa': resa.date_reservation.strftime('%d/%m/%Y') if resa.date_reservation else '',
            'statut': resa.statut,
            'vols': []
        }
        
        vols_map = {}
        for billet in resa.billets:
            vol = billet.vol
            if not vol: continue
            
            if vol.id_vol not in vols_map:
                dep_time_local = get_local_time(vol.date_heure_dep_utc, vol.id_aeroport_depart)
                arr_time_local = get_local_time(vol.date_heure_arr_utc, vol.id_aeroport_arrivee)
                is_delayed = vol.statut.lower() not in ["à l'heure", "embarquement", "confirme"]
                
                vols_map[vol.id_vol] = {
                    'flight_number': f"OB{vol.id_vol}",
                    'date': dep_time_local.strftime('%d %B %Y'),
                    'dep_time': dep_time_local.strftime('%H:%M'),
                    'dep_iata': vol.id_aeroport_depart,
                    'dep_city': vol.aeroport_depart.ville if vol.aeroport_depart else vol.id_aeroport_depart,
                    'arr_time': arr_time_local.strftime('%H:%M'),
                    'arr_iata': vol.id_aeroport_arrivee,
                    'arr_city': vol.aeroport_arrivee.ville if vol.aeroport_arrivee else vol.id_aeroport_arrivee,
                    'status_text': vol.statut.capitalize(),
                    'status_class': 'status-delayed' if is_delayed else 'status-ontime',
                    'journey_type': 'aller' if vol.id_vol in aller_ids else 'retour',
                    'sort_time': vol.date_heure_dep_utc,
                    'passagers': []
                }
                
            vols_map[vol.id_vol]['passagers'].append({
                'nom': billet.passager.nom if billet.passager else 'N/A',
                'prenom': billet.passager.prenom if billet.passager else 'N/A',
                'classe': billet.classe,
                'seat': billet.siege or 'Non assigné',
                'meal': repas_map.get(billet.options_repas, 'Standard'),
                'baggage': f"{billet.bagages_sup} en soute"
            })
            
        resa_dict['vols'] = sorted(list(vols_map.values()), key=lambda x: x['sort_time'])
        reservations_data.append(resa_dict)
            
    return render_template('client/mes_reservations.html', reservations=reservations_data)

@client_bp.route('/gerer-reservation/<pnr>', methods=['GET', 'POST'])
@login_required
def gerer_reservation(pnr):
    """Gérer une réservation spécifique (Master access)"""
    if session.get('modifying_pnr') or session.get('search_params'):
        clear_booking_session()
        
    user_id = session.get('user_id')
    
    # Sécurisation : Seul le client ayant fait la réservation peut y accéder
    reservation = db.session.query(Reservation).filter_by(pnr=pnr, id_client=user_id).first_or_404()

    aller_vols_obj, _ = group_flights_by_journey(reservation.billets)
    aller_ids = {v.id_vol for v in aller_vols_obj}
    
    repas_map = {0: 'Standard', 1: 'Premium', 2: 'Végétarien', 3: 'Gastronomique'}
    vols_map = {}
    
    # Déballage de la hiérarchie Master -> Passagers -> Options
    for billet in reservation.billets:
        vol = billet.vol
        if not vol: continue
        
        if vol.id_vol not in vols_map:
            dep_time_local = get_local_time(vol.date_heure_dep_utc, vol.id_aeroport_depart)
            arr_time_local = get_local_time(vol.date_heure_arr_utc, vol.id_aeroport_arrivee)
            is_delayed = vol.statut.lower() not in ["à l'heure", "embarquement", "confirme"]
            
            vols_map[vol.id_vol] = {
                'flight_number': f"OB{vol.id_vol}",
                'dep_iata': vol.id_aeroport_depart,
                'dep_city': vol.aeroport_depart.ville if vol.aeroport_depart else vol.id_aeroport_depart,
                'arr_iata': vol.id_aeroport_arrivee,
                'arr_city': vol.aeroport_arrivee.ville if vol.aeroport_arrivee else vol.id_aeroport_arrivee,
                'date': dep_time_local.strftime('%d/%m/%Y'),
                'dep_time': dep_time_local.strftime('%H:%M'),
                'arr_time': arr_time_local.strftime('%H:%M'),
                'status_text': vol.statut.capitalize(),
                'status_class': 'status-delayed' if is_delayed else 'status-ontime',
                'sort_time': vol.date_heure_dep_utc,
                'passagers': []
            }
            
        vols_map[vol.id_vol]['passagers'].append({
            'nom': billet.passager.nom if billet.passager else 'N/A',
            'prenom': billet.passager.prenom if billet.passager else 'N/A',
            'classe': billet.classe,
            'seat': billet.siege or 'Non assigné',
            'meal': repas_map.get(billet.options_repas, 'Standard'),
            'baggage': f"{billet.bagages_sup} en soute"
        })
        
    resa_data = {
        'pnr': reservation.pnr,
        'statut': reservation.statut,
        'vols': sorted(list(vols_map.values()), key=lambda x: x['sort_time'])
    }
    
    return render_template('client/gerer_reservation.html', reservation=resa_data)

@client_bp.route('/init-modification/<pnr>')
@login_required
def init_modification(pnr):
    """
    Action Modification : Initialise la session du tunnel avec les données de la réservation existante (PNR),
    puis redirige l'utilisateur vers les vues de recherche ou d'options pour y apporter des changements.
    """
    reservation = db.session.query(Reservation).filter_by(pnr=pnr, id_client=session['user_id']).first_or_404()
    billets = reservation.billets
    if not billets:
        flash("Réservation invalide.", "danger")
        return redirect(url_for('client.mes_reservations'))
        
    passagers, vols = {}, {}
    for b in billets:
        if b.id_passager not in passagers: passagers[b.id_passager] = b.passager
        if b.id_vol not in vols: vols[b.id_vol] = b.vol
            
    vols_list = sorted(list(vols.values()), key=lambda v: v.date_heure_dep_utc)
    is_ar = False
    if len(vols_list) > 1 and vols_list[-1].id_aeroport_arrivee == vols_list[0].id_aeroport_depart:
        is_ar = True
        # Trouver la césure (le vol de retour) en cherchant le temps d'escale le plus long
        max_gap_idx = 1
        max_gap = 0
        for i in range(1, len(vols_list)):
            gap = (vols_list[i].date_heure_dep_utc - vols_list[i-1].date_heure_arr_utc).total_seconds()
            if gap > max_gap:
                max_gap = gap
                max_gap_idx = i
                
        aller_vols = vols_list[:max_gap_idx]
        retour_vols = vols_list[max_gap_idx:]
    else:
        aller_vols = vols_list
        retour_vols = []

    search_params = {
        'depart': aller_vols[0].id_aeroport_depart, 'arrivee': aller_vols[-1].id_aeroport_arrivee,
        'type_vol': 'AR' if is_ar else 'AS', 'passagers': str(len(passagers)),
        'date_aller': aller_vols[0].date_heure_dep_utc.strftime('%Y-%m-%d'),
        'date_retour': retour_vols[0].date_heure_dep_utc.strftime('%Y-%m-%d') if is_ar and retour_vols else ''
    }
    
    passagers_list = sorted(list(passagers.values()), key=lambda p: p.id_passager)
    passagers_data = {}
    options_passagers, classes_aller, classes_retour = [], [], []
    repas_map_rev = {0: 'standard', 1: 'premium', 2: 'vegetarien', 3: 'gastronomique'}
    prix_options_total = 0
    
    for i, p in enumerate(passagers_list, start=1):
        passagers_data[f'prenom_{i}'] = p.prenom
        passagers_data[f'nom_{i}'] = p.nom
        passagers_data[f'civilite_{i}'] = 'M.'
        
        p_billets = [b for b in billets if b.id_passager == p.id_passager]
        
        # Respect strict de l'ordre chronologique des vols
        p_billets_aller = []
        for v in aller_vols:
            found = False
            for b in p_billets:
                if b.id_vol == v.id_vol:
                    p_billets_aller.append(b)
                    found = True
                    break
            if not found:
                p_billets_aller.append(None)
                    
        p_billets_retour = []
        for v in retour_vols:
            found = False
            for b in p_billets:
                if b.id_vol == v.id_vol:
                    p_billets_retour.append(b)
                    found = True
                    break
            if not found:
                p_billets_retour.append(None)
        
        c_aller = p_billets_aller[0].classe if p_billets_aller and p_billets_aller[0] else 'Eco'
        c_retour = p_billets_retour[0].classe if p_billets_retour and p_billets_retour[0] else 'Eco'
        classes_aller.append(c_aller)
        classes_retour.append(c_retour)
        
        bag_val = p_billets_aller[0].bagages_sup if p_billets_aller and p_billets_aller[0] else 0
        rep_idx = p_billets_aller[0].options_repas if p_billets_aller and p_billets_aller[0] else 0
        rep_str = repas_map_rev.get(rep_idx, 'standard')

        rank_aller = {'Eco':1, 'Business':2, 'First':3}.get(c_aller, 1)
        rank_retour = {'Eco':1, 'Business':2, 'First':3}.get(c_retour, 1)
        highest_class = 'First' if max(rank_aller, rank_retour) == 3 else 'Business' if max(rank_aller, rank_retour) == 2 else 'Eco'
        
        if highest_class == 'Eco':
            prix_options_total += TARIFS_OPTIONS['bagages_eco'].get(str(bag_val), 0)
            prix_options_total += TARIFS_OPTIONS['repas_eco'].get(rep_str, 0)
        elif highest_class in ['Business', 'First']:
            prix_options_total += TARIFS_OPTIONS['bagages_eco'].get(str(bag_val), 0)

        options_passagers.append({
            'bagages': f"{bag_val}_23kg" if p_billets_aller else "0",
            'repas': rep_str,
            'classe_aller': c_aller, 'classe_retour': c_retour,
            'sieges_aller': [(b.siege if b and b.siege else '') for b in p_billets_aller],
            'sieges_retour': [(b.siege if b and b.siege else '') for b in p_billets_retour]
        })

    def get_flight_pricing(vols_subset):
        if not vols_subset: return None
        base_price = sum(float(v.prix_de_base) for v in vols_subset)
        if len(vols_subset) == 2: base_price *= 0.85
        elif len(vols_subset) >= 3: base_price *= 0.75
        if is_ar: base_price *= 0.9
        return {
            'id_vol': "_".join(str(v.id_vol) for v in vols_subset), 'classe': 'Mixte',
            'classes': [], 'prix': 0, 'prix_eco': max(50, base_price),
            'prix_biz': base_price * 2.5, 'prix_first': base_price * 4.0
        }

    nb_pass = len(passagers_list)
    vol_aller = get_flight_pricing(aller_vols)
    if vol_aller: 
        vol_aller['classes'] = classes_aller
        total_aller_price = sum(vol_aller[{'Eco':'prix_eco', 'Business':'prix_biz', 'First':'prix_first'}.get(c, 'prix_eco')] for c in classes_aller)
        vol_aller['prix'] = total_aller_price / nb_pass if nb_pass > 0 else 0
        
    vol_retour = get_flight_pricing(retour_vols)
    if vol_retour: 
        vol_retour['classes'] = classes_retour
        total_retour_price = sum(vol_retour[{'Eco':'prix_eco', 'Business':'prix_biz', 'First':'prix_first'}.get(c, 'prix_eco')] for c in classes_retour)
        vol_retour['prix'] = total_retour_price / nb_pass if nb_pass > 0 else 0

    session['search_params'] = search_params
    session['passagers_data'] = passagers_data
    session['vol_aller'] = vol_aller
    if vol_retour: session['vol_retour'] = vol_retour
    session['options'] = {'passagers': options_passagers, 'prix': prix_options_total / nb_pass if nb_pass > 0 else 0}
    session['modifying_pnr'] = pnr
    
    update_total_panier()
    session['original_total'] = session.get('total_panier', 0)
    session['highlight_option'] = f"{request.args.get('highlight')}_{request.args.get('p_index')}"
    session.modified = True
    
    if request.args.get('target') == 'classe':
        return redirect(url_for('client.booking_flights'))
    return redirect(url_for('client.booking_options'))