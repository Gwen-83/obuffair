"""
Routes admin : CRUD vols/avions/aéroports, configuration tarifaire, dashboards analytiques.
Gère aussi les droits d'accès et logs d'audit.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort, current_app
from app.portail_auth.decorators import admin_required
from app import db
from app.model import Avion, Vols, Support, Aeroport, User
from app.portail_admin.forms import FormAjouterAvion, FormAeroport
from sqlalchemy import text
from types import SimpleNamespace
from datetime import datetime, timezone
from app.algos.yield_management import calculer_prix
from app.portail_admin.emails_utils import send_flight_cancellation_email

_aeroports_schema_verified = False

def ensure_aeroports_decalage_column():
    global _aeroports_schema_verified
    if _aeroports_schema_verified:
        return
    try:
        result = db.session.execute(
            text(
                "SELECT CHARACTER_MAXIMUM_LENGTH "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'aeroports' "
                "AND column_name = 'decalage_utc'"
            )
        ).fetchone()
        if result and (result[0] is None or result[0] < 10):
            db.session.execute(
                text(
                    "ALTER TABLE aeroports MODIFY COLUMN decalage_utc VARCHAR(10) NOT NULL DEFAULT '+00:00'"
                )
            )
            db.session.commit()
    except Exception:
        db.session.rollback()
    finally:
        _aeroports_schema_verified = True

# Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    nb_vols = db.session.execute(db.text("SELECT COUNT(*) FROM vols ")).fetchone()
    nb_resa = db.session.execute(db.text("SELECT COUNT(*) FROM reservations WHERE statut = 'Confirmee' ")).fetchone()
    # Récupérer vols + model avion + capacité tot et nbr de résa/vol
    vols_rows = db.session.execute(text("""
        SELECT v.*,
               a.modele,
               (a.nb_rangees * a.largeur_rangee) AS capacite_totale,
               COALESCE(SUM(CASE WHEN r.statut = 'Confirmee' THEN 1 ELSE 0 END), 0) AS nb_reservations
        FROM vols v
        LEFT JOIN avions a ON a.immatriculation = v.immatriculation_avion
        LEFT JOIN billets b ON b.id_vol = v.id_vol
        LEFT JOIN reservations r ON b.id_reservation = r.id_reservation
        GROUP BY v.id_vol
    """)).mappings().all()

    # calcul pourcentage remplissage/vol
    vols = []
    for row in vols_rows:
        d = dict(row)
        capacite = d.get('capacite_totale') or 0
        nb_resa_vol = d.get('nb_reservations') or 0
        d['fill_percent'] = int((nb_resa_vol / capacite) * 100) if capacite > 0 else 0
        vols.append(d)
    return render_template('admin/html/dashboard.html', nb_vols=nb_vols, nb_resa=nb_resa, vols=vols)

@admin_bp.route('/config_avion', methods=['GET', 'POST'])
@admin_required
def config_avion():
    """Configuration des cabines et gestion de la flotte d'avions"""
    form = FormAjouterAvion()
    
    # Récupérer tous les avions
    avions = db.session.execute(text("""SELECT *,(nb_rangees * largeur_rangee) AS capacite_totale FROM avions""")).mappings().all()
    
    # Formulaire ajout avins
    if form.validate_on_submit():
        immat_upper = form.immatriculation.data.upper()
        try:
            nouvel_avion = Avion(
                immatriculation=immat_upper,
                modele=form.modele.data or '',
                nb_rangees=form.nb_rangees.data or 0,
                largeur_rangee=form.largeur_rangee.data or 0,
                eco_rang_de=form.eco_rang_de.data or 0,
                eco_rang_a=form.eco_rang_a.data or 0,
                bus_rang_de=form.bus_rang_de.data or 0,
                bus_rang_a=form.bus_rang_a.data or 0,
                first_rang_de=form.first_rang_de.data or 0,
                first_rang_a=form.first_rang_a.data or 0,
                actif=form.actif.data if form.actif.data is not None else True
            )
            db.session.add(nouvel_avion)
            db.session.commit()
            flash(f'Avion {nouvel_avion.immatriculation} ajouté', 'success')
            return redirect(url_for('admin.config_avion'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'ajout : {str(e)}', 'danger')
    
    return render_template('admin/html/config_avion.html', avions=avions, form=form)

@admin_bp.route('/infrastructures', methods=['GET', 'POST'])
@admin_required
def infrastructures():
    """Gestion des aéroports et de leurs infrastructures."""
    selected_id = request.args.get('selected', '').upper()
    original_id = request.form.get('original_id') or selected_id
    form = FormAeroport(original_id=original_id)
    selected_airport = None

    ensure_aeroports_decalage_column()

    if form.validate_on_submit():
        original_id = form.original_id.data or form.id_aeroport.data
        id_aeroport = form.id_aeroport.data.upper()
        try:
            existing_aeroport = db.session.execute(
                text("SELECT id_aeroport FROM aeroports WHERE id_aeroport = :id"),
                {'id': original_id}
            ).fetchone()

            if existing_aeroport:
                db.session.execute(
                    text(
                        "UPDATE aeroports SET id_aeroport = :new_id, nom = :nom, ville = :ville, pays = :pays, decalage_utc = :utc, "
                        "latitude = :latitude, longitude = :longitude, terminals_count = :terminals_count, gates_total = :gates_total, "
                        "lounges_count = :lounges_count, parkings_count = :parkings_count, services = :services, contact_phone = :contact_phone, "
                        "contact_email = :contact_email, description = :description "
                        "WHERE id_aeroport = :orig"
                    ),
                    {
                        'new_id': id_aeroport,
                        'nom': form.nom.data,
                        'ville': form.ville.data,
                        'pays': form.pays.data,
                        'utc': form.decalage_utc.data,
                        'latitude': form.latitude.data,
                        'longitude': form.longitude.data,
                        'terminals_count': form.terminals_count.data or 0,
                        'gates_total': form.gates_total.data or 0,
                        'lounges_count': form.lounges_count.data or 0,
                        'parkings_count': form.parkings_count.data or 0,
                        'services': form.services.data,
                        'contact_phone': form.contact_phone.data,
                        'contact_email': form.contact_email.data,
                        'description': form.description.data,
                        'orig': original_id
                    }
                )
            else:
                db.session.execute(
                    text(
                        "INSERT INTO aeroports (id_aeroport, nom, ville, pays, decalage_utc, latitude, longitude, terminals_count, gates_total, lounges_count, parkings_count, services, contact_phone, contact_email, description) "
                        "VALUES (:id_aeroport, :nom, :ville, :pays, :utc, :latitude, :longitude, :terminals_count, :gates_total, :lounges_count, :parkings_count, :services, :contact_phone, :contact_email, :description)"
                    ),
                    {
                        'id_aeroport': id_aeroport,
                        'nom': form.nom.data,
                        'ville': form.ville.data,
                        'pays': form.pays.data,
                        'utc': form.decalage_utc.data,
                        'latitude': form.latitude.data,
                        'longitude': form.longitude.data,
                        'terminals_count': form.terminals_count.data or 0,
                        'gates_total': form.gates_total.data or 0,
                        'lounges_count': form.lounges_count.data or 0,
                        'parkings_count': form.parkings_count.data or 0,
                        'services': form.services.data,
                        'contact_phone': form.contact_phone.data,
                        'contact_email': form.contact_email.data,
                        'description': form.description.data
                    }
                )
            db.session.commit()
            flash(f'Aéroport {id_aeroport} enregistré avec succès', 'success')
            return redirect(url_for('admin.infrastructures', selected=id_aeroport))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l’enregistrement : {str(e)}', 'danger')

    if selected_id:
        selected_row = db.session.execute(
            text(
                "SELECT a.id_aeroport, a.nom, a.ville, a.pays, a.decalage_utc, a.latitude, a.longitude, "
                "COALESCE(a.terminals_count, 0) AS terminals_count, COALESCE(a.gates_total, 0) AS gates_total, "
                "COALESCE(a.lounges_count, 0) AS lounges_count, COALESCE(a.parkings_count, 0) AS parkings_count, "
                "a.services, a.contact_phone, a.contact_email, a.description "
                "FROM aeroports a "
                "WHERE a.id_aeroport = :code LIMIT 1"
            ),
            {'code': selected_id}
        ).mappings().first()
        if selected_row:
            selected_airport = dict(selected_row)
            if request.method == 'GET':
                form.id_aeroport.data = selected_airport['id_aeroport']
                form.nom.data = selected_airport['nom']
                form.ville.data = selected_airport['ville']
                form.pays.data = selected_airport['pays']
                form.decalage_utc.data = selected_airport['decalage_utc']
                form.latitude.data = selected_airport['latitude']
                form.longitude.data = selected_airport['longitude']
                form.terminals_count.data = selected_airport['terminals_count']
                form.gates_total.data = selected_airport['gates_total']
                form.lounges_count.data = selected_airport['lounges_count']
                form.parkings_count.data = selected_airport['parkings_count']
                form.services.data = selected_airport['services']
                form.contact_phone.data = selected_airport['contact_phone']
                form.contact_email.data = selected_airport['contact_email']
                form.description.data = selected_airport['description']
                form.original_id.data = selected_airport['id_aeroport']
        else:
            flash('Aéroport introuvable', 'danger')
            return redirect(url_for('admin.infrastructures'))

    aeroport_rows = db.session.execute(
        text(
            "SELECT a.id_aeroport, a.nom, a.ville, a.pays, a.decalage_utc, "
            "COALESCE(a.terminals_count, 0) AS terminals_count, COALESCE(a.gates_total, 0) AS gates_total, "
            "COALESCE(a.lounges_count, 0) AS lounges_count, COALESCE(a.parkings_count, 0) AS parkings_count "
            "FROM aeroports a "
            "ORDER BY a.ville, a.nom"
        )
    ).mappings().all()

    aeroport_rows = [dict(row) for row in aeroport_rows]

    return render_template('admin/html/infrastructures.html', airports=aeroport_rows, form=form, selected_airport=selected_airport)


@admin_bp.route('/aeroports/<string:id_aeroport>/delete', methods=['POST'])
@admin_required
def supprimer_aeroport(id_aeroport):
    try:
        db.session.execute(text('DELETE FROM aeroports WHERE id_aeroport = :id'), {'id': id_aeroport})
        db.session.commit()
        flash(f'Aéroport {id_aeroport} supprimé', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur suppression : {str(e)}', 'danger')
    return redirect(url_for('admin.infrastructures'))


@admin_bp.route('/api/avion/<string:immatriculation>', methods=['DELETE'])
@admin_required
def supprimer_avion(immatriculation):
    """supprimer avion en désactivant (actif = 0 bdd)"""
    result = db.session.execute(db.text("UPDATE avions SET actif = false WHERE immatriculation = :immat"),{"immat": immatriculation}
    )
    if result.rowcount == 0:
        abort(404)
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'Avion {immatriculation} supprimé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/avion/<string:immatriculation>/edit', methods=['GET', 'POST'])
@admin_required
def edit_avion(immatriculation):
    """Modifier un avion existant"""
    row = db.session.execute(text("SELECT * FROM avions WHERE immatriculation = :immat LIMIT 1"),{"immat": immatriculation}).mappings().first()
    if not row:
        abort(404)
    avion = SimpleNamespace(**dict(row))
    form = FormAjouterAvion(original_immatriculation=avion.immatriculation)

    if request.method == 'GET':
        # Pré-remplir formulaire avec info bdd
        form.immatriculation.data = avion.immatriculation
        form.modele.data = avion.modele
        form.nb_rangees.data = avion.nb_rangees
        form.largeur_rangee.data = avion.largeur_rangee
        form.eco_rang_de.data = avion.eco_rang_de
        form.eco_rang_a.data = avion.eco_rang_a
        form.bus_rang_de.data = avion.bus_rang_de
        form.bus_rang_a.data = avion.bus_rang_a
        form.first_rang_de.data = avion.first_rang_de
        form.first_rang_a.data = avion.first_rang_a
        form.actif.data = avion.actif

    if form.validate_on_submit():
        try:
            # Pas de changement immat en edit
            db.session.execute(
                text(
                    "UPDATE avions SET modele = :modele, nb_rangees = :nb_rangees, largeur_rangee = :largeur_rangee, eco_rang_de = :eco_rang_de, eco_rang_a = :eco_rang_a, bus_rang_de = :bus_rang_de, bus_rang_a = :bus_rang_a, first_rang_de = :first_rang_de, first_rang_a = :first_rang_a, actif = :actif WHERE immatriculation = :immat"
                ),
                {
                    "modele": form.modele.data or '',
                    "nb_rangees": form.nb_rangees.data or 0,
                    "largeur_rangee": form.largeur_rangee.data or 0,
                    "eco_rang_de": form.eco_rang_de.data or 0,
                    "eco_rang_a": form.eco_rang_a.data or 0,
                    "bus_rang_de": form.bus_rang_de.data or 0,
                    "bus_rang_a": form.bus_rang_a.data or 0,
                    "first_rang_de": form.first_rang_de.data or 0,
                    "first_rang_a": form.first_rang_a.data or 0,
                    "actif": form.actif.data if form.actif.data is not None else True,
                    "immat": immatriculation
                }
            )
            db.session.commit()
            flash(f'Avion {immatriculation} modifié', 'success')
            return redirect(url_for('admin.config_avion'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification : {str(e)}', 'danger')

    return render_template('admin/html/edit_avion.html', form=form, avion=avion)

@admin_bp.route('/vols')
@admin_required
def gestion_vols():
    """Affiche la page du calendrier des vols et la liste détaillée"""

    avions = db.session.execute(text("SELECT immatriculation, modele FROM avions WHERE actif = true")).mappings().all()
    aeroports = db.session.execute(text("SELECT id_aeroport, nom, ville, pays FROM aeroports ORDER BY ville")).mappings().all()
    
    # Récupération liste vols
    vols_list = db.session.execute(text("""
        SELECT v.*,
               a_dep.ville AS ville_depart,
               a_arr.ville AS ville_arrivee
        FROM vols v
        LEFT JOIN aeroports a_dep ON v.id_aeroport_depart = a_dep.id_aeroport
        LEFT JOIN aeroports a_arr ON v.id_aeroport_arrivee = a_arr.id_aeroport
        ORDER BY v.date_heure_dep_utc DESC
    """)).mappings().all()

    return render_template('admin/html/vols.html', avions=avions, aeroports=aeroports, vols_list=vols_list)


@admin_bp.route('/reservations')
@admin_required
def reservations():
    """Liste des réservations avec leurs billets associés"""
    # Récupérer réservations
    réservations = db.session.execute(text("""
        SELECT id_reservation, id_client, date_reservation, statut
        FROM reservations
        ORDER BY date_reservation DESC
    """)).mappings().all()

    reservations = []
    for résa in réservations:
        résa_dico = dict(résa)
        # formater date lisible
        dt = résa_dico.get('date_reservation')
        if hasattr(dt, 'strftime'):
            résa_dico['date_reservation'] = dt.strftime('%Y-%m-%d %H:%M')

        # récupérer billets liés
        billets = db.session.execute(text("""
            SELECT id_billet, id_vol, classe, options_repas, bagages_sup
            FROM billets
            WHERE id_reservation = :rid
            ORDER BY id_billet
        """), {"rid": résa_dico['id_reservation']}).mappings().all()

        résa_dico['billets'] = [dict(b) for b in billets]
        reservations.append(résa_dico)

    return render_template('admin/html/reservations.html', reservations=reservations)

@admin_bp.route('/tarification', methods=['GET'])
@admin_required
def tarification():
    """Afficher les vols avec prix base et prix suggéré par l'algorithme"""
    rows = db.session.execute(text("""
        SELECT v.id_vol, v.id_aeroport_depart, v.id_aeroport_arrivee, v.date_heure_dep_utc, v.prix_de_base,
               a.nb_rangees, a.largeur_rangee, COALESCE(SUM(CASE WHEN r.statut = 'Confirmee' THEN 1 ELSE 0 END),0) AS nb_reservations
        FROM vols v
        LEFT JOIN avions a ON a.immatriculation = v.immatriculation_avion
        LEFT JOIN billets b ON b.id_vol = v.id_vol
        LEFT JOIN reservations r ON b.id_reservation = r.id_reservation
        GROUP BY v.id_vol
        ORDER BY v.date_heure_dep_utc DESC
    """)).mappings().all()

    vols = []
    for row in rows:
        d = dict(row)
        capacite = (d.get('nb_rangees') or 0) * (d.get('largeur_rangee') or 0)
        taux = (d.get('nb_reservations') or 0) / capacite if capacite > 0 else 0.0

        try:
            resultat = calculer_prix(
                prix_de_base=float(d.get('prix_de_base') or 0),
                date_depart=d.get('date_heure_dep_utc'),
                date_calcul=datetime.utcnow(),
                taux_remplissage_vol=float(taux),
                taux_remplissage_classe=float(taux),
                classe='eco'
            )
            suggested = resultat.get('prix_final') if isinstance(resultat, dict) else d.get('prix_de_base')
        except Exception:
            suggested = d.get('prix_de_base')

        d['capacite'] = capacite
        d['taux'] = round(taux, 3)
        d['suggested'] = suggested
        vols.append(d)

    return render_template('admin/html/tarification.html', vols=vols)


@admin_bp.route('/tarification/update', methods=['POST'])
@admin_required
def update_tarif():
    vol_id = request.form.get('vol_id')
    new_price = request.form.get('new_price')
    try:
        p = float(new_price)
    except Exception:
        flash('Prix invalide', 'danger')
        return redirect(url_for('admin.tarification'))

    try:
        db.session.execute(text("UPDATE vols SET prix_de_base = :p WHERE id_vol = :id"), {'p': p, 'id': vol_id})
        db.session.commit()
        flash('Prix mis à jour', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur mise à jour: {str(e)}', 'danger')

    return redirect(url_for('admin.tarification'))


@admin_bp.route('/support')
@admin_required
def support():
    """Liste des tickets de support avec statistiques"""
    # Récupérer tous les tickets
    tickets = db.session.query(Support).order_by(Support.date_creation.desc()).all()
    
    # Calculer les statistiques par statut
    stats = {
        'nouveau': db.session.query(Support).filter(Support.statut == 'nouveau').count(),
        'en_cours': db.session.query(Support).filter(Support.statut == 'en cours').count(),
        'resolu': db.session.query(Support).filter(Support.statut == 'resolu').count(),
        'ferme': db.session.query(Support).filter(Support.statut == 'ferme').count(),
    }
    
    # Formater les dates
    for t in tickets:
        t.date_creation = t.date_creation.strftime('%Y-%m-%d %H:%M') if hasattr(t.date_creation, 'strftime') else t.date_creation
    
    return render_template('admin/html/support.html', tickets=tickets, stats=stats)

@admin_bp.route('/support/<int:id_ticket>', methods=['GET', 'POST'])
@admin_required
def support_detail(id_ticket):
    """Détail et réponse à un ticket de support"""
    ticket = db.session.get(Support, id_ticket)
    if not ticket:
        flash('Ticket introuvable.', 'danger')
        return redirect(url_for('admin.support'))

    # Récupérer l'email du client s'il existe (pour réponse par mail)
    user_email = None
    try:
        if getattr(ticket, 'id_client', None):
            user = db.session.get(User, ticket.id_client)
            if user and getattr(user, 'email', None):
                user_email = user.email
    except Exception:
        user_email = None

    ticket.date_creation = ticket.date_creation.strftime('%Y-%m-%d %H:%M') if hasattr(ticket.date_creation, 'strftime') else ticket.date_creation
    ticket.date_modification = ticket.date_modification.strftime('%Y-%m-%d %H:%M') if hasattr(ticket.date_modification, 'strftime') else ticket.date_modification
    return render_template('admin/html/support_detail.html', ticket=ticket, user_email=user_email)

@admin_bp.route('/api/vols', methods=['GET'])
@admin_required
def get_vols():
    vols_rows = db.session.execute(text("""
        SELECT v.*,
               a.modele,
               (a.nb_rangees * a.largeur_rangee) AS capacite_totale,
               COALESCE(SUM(CASE WHEN r.statut = 'Confirmee' THEN 1 ELSE 0 END), 0) AS nb_reservations
        FROM vols v
        LEFT JOIN avions a ON a.immatriculation = v.immatriculation_avion
        LEFT JOIN billets b ON b.id_vol = v.id_vol
        LEFT JOIN reservations r ON b.id_reservation = r.id_reservation
        GROUP BY v.id_vol, a.immatriculation, a.modele
    """)).mappings().all()

    events = []
    for v in vols_rows:
        bg_color = '#002A5C'
        if v['statut'] == 'retardé': bg_color = '#F57C00'
        elif v['statut'] == 'annulé': bg_color = '#C62828'
        elif v['statut'] == 'embarquement': bg_color = '#2E7D32'
        
        capacite = v['capacite_totale'] or 0
        nb_resa_vol = v['nb_reservations'] or 0
        fill_percent = int((nb_resa_vol / capacite) * 100) if capacite > 0 else 0
        
        events.append({
            'id': v['id_vol'],
            'title': f"{v['id_aeroport_depart']} ✈ {v['id_aeroport_arrivee']}",
            'start': v['date_heure_dep_utc'].isoformat() + 'Z',
            'end': v['date_heure_arr_utc'].isoformat() + 'Z' if v['date_heure_arr_utc'] else None,
            'backgroundColor': bg_color,
            'borderColor': '#FFC72C',
            'resourceId': v['modele'],
            'extendedProps': {
                'avion': v['immatriculation_avion'],
                'depart': v['id_aeroport_depart'],
                'arrivee': v['id_aeroport_arrivee'],
                'prix': str(v['prix_de_base']),
                'statut': v['statut'],
                'fill_percent': fill_percent
            }
        })
    return jsonify(events)

@admin_bp.route('/api/vols', methods=['POST'])
@admin_required
def create_vol():
    """API : Créer un nouveau vol"""
    data = request.json
    try:
        def parse_date_to_utc(date_str):
            if not date_str: return None
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        
        start_time = parse_date_to_utc(data['start'])
        end_time = parse_date_to_utc(data['end'])
        avion_immat = data['avion']
        
        # Pas de chevauchement d'horaire
        conflits = db.session.execute(text("""
            SELECT * FROM vols 
            WHERE immatriculation_avion = :avion_immat
              AND date_heure_dep_utc < :end_time
              AND date_heure_arr_utc > :start_time
            LIMIT 1
        """), {
            "avion_immat": avion_immat,
            "end_time": end_time,
            "start_time": start_time
        }).mappings().first()
        
        if conflits:
            return jsonify({
                'success': False,
                'message': f"Conflit détecté : l'avion {avion_immat} a déjà un vol programmé pendant cette période (Vol #{conflits.id_vol})"
            }), 409
        
        nouveau_vol = Vols(
            immatriculation_avion=avion_immat,
            id_aeroport_depart=data['depart'].upper(),
            id_aeroport_arrivee=data['arrivee'].upper(),
            date_heure_dep_utc=start_time,
            date_heure_arr_utc=end_time,
            prix_de_base=float(data['prix']),
            statut=data.get('statut', "à l'heure")
        )
            
        db.session.add(nouveau_vol)
        db.session.commit()
        return jsonify({'success': True, 'id': nouveau_vol.id_vol})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/api/vols/<int:id_vol>', methods=['PUT'])
@admin_required
def update_vol(id_vol):
    """API : Maj vol"""
    data = request.json
    
    # CORRECTION ICI : On utilise l'ORM pour récupérer un Objet modifiable
    vol = Vols.query.get(id_vol)

    if not vol:
        return jsonify({'success': False, 'message': 'Vol introuvable'}), 404
        
    try:
        def parse_date_to_utc(date_str):
            if not date_str: return None
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
            
        nouvel_avion = data.get('avion', vol.immatriculation_avion)
        nouveau_start = vol.date_heure_dep_utc
        nouveau_end = vol.date_heure_arr_utc
        
        if 'start' in data and data['start']:
            nouveau_start = parse_date_to_utc(data['start'])
        if 'end' in data and data['end']:
            nouveau_end = parse_date_to_utc(data['end'])
        
        # Vérification des conflits avec l'ORM
        conflits = Vols.query.filter(
            Vols.immatriculation_avion == nouvel_avion,
            Vols.id_vol != id_vol,
            Vols.date_heure_dep_utc < nouveau_end,
            Vols.date_heure_arr_utc > nouveau_start
        ).first()
        
        if conflits:
            return jsonify({
                'success': False,
                'message': f"Conflit détecté : l'avion {nouvel_avion} a déjà un vol programmé pendant cette période (Vol #{conflits.id_vol})"
            }), 409
        
        # Mise à jour des attributs de l'objet
        if 'depart' in data: 
            vol.id_aeroport_depart = data['depart'].upper()
        if 'arrivee' in data: 
            vol.id_aeroport_arrivee = data['arrivee'].upper()
        if 'avion' in data: 
            vol.immatriculation_avion = data['avion']
        if 'prix' in data:
            vol.prix_de_base = float(data['prix'])
        if 'statut' in data and data['statut']: 
            vol.statut = data['statut']
        
        vol.date_heure_dep_utc = nouveau_start
        vol.date_heure_arr_utc = nouveau_end
            
        # Sauvegarde en base de données
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/api/vols/<int:id_vol>/reservations_count', methods=['GET'])
@admin_required
def count_reservations_vol(id_vol):
    """API : Compte les réservations actives liées à un vol"""
    row = db.session.execute(text("""
        SELECT COUNT(DISTINCT r.id_reservation) AS nb
        FROM billets b
        JOIN reservations r ON r.id_reservation = b.id_reservation
        WHERE b.id_vol = :id_vol
          AND r.statut != 'Annulee'
    """), {"id_vol": id_vol}).fetchone()
    return jsonify({"nb_reservations": row[0] if row else 0})

@admin_bp.route('/api/vols/<int:id_vol>', methods=['DELETE'])
@admin_required
def delete_vol(id_vol):
    """API : Supprimer un vol, annuler ses réservations associées et notifier les clients"""
    vol = db.session.get(Vols, id_vol)
    if not vol:
        return jsonify({'success': False, 'message': 'Vol introuvable'}), 404
        
    try:
        # 1. Récupérer les informations des clients impactés AVANT la suppression
        # Utilisation de .mappings() pour accéder aux colonnes par leur nom comme un dictionnaire
        impacted_data = db.session.execute(text("""
            SELECT DISTINCT c.email, c.prenom, c.nom, r.pnr, r.id_reservation
            FROM billets b
            JOIN reservations r ON b.id_reservation = r.id_reservation
            JOIN clients c ON r.id_client = c.id_client
            WHERE b.id_vol = :id_vol AND r.statut != 'Annulee'
        """), {"id_vol": id_vol}).mappings().fetchall()

        resa_ids = [row['id_reservation'] for row in impacted_data]

        # 2. Envoyer les emails de notification avec la même méthode que l'auth
        for data in impacted_data:
            send_flight_cancellation_email(
                user_email=data['email'],
                prenom=data['prenom'],
                nom=data['nom'],
                pnr=data['pnr'],
                app=current_app
            )

        # 3. Supprimer les données en base si des réservations sont touchées
