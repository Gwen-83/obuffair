"""
Routes admin : CRUD vols/avions/aéroports, configuration tarifaire, dashboards analytiques.
Gère aussi les droits d'accès et logs d'audit.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from app.portail_auth.decorators import admin_required
from app import db
from app.portail_admin.modele_admin import Avion
from app.portail_admin.forms import FormAjouterAvion
from app.portail_admin.modele_admin import Vols
from sqlalchemy import text
from types import SimpleNamespace
from datetime import datetime
# Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    nb_vols = db.session.execute(db.text("SELECT COUNT(*) FROM vols ")).fetchone()
    nb_resa = db.session.execute(db.text("SELECT COUNT(*) FROM reservations ")).fetchone()
    # Récupérer vols + model avion + capacité tot et nbr de résa/vol
    vols_rows = db.session.execute(text("""
        SELECT v.*,
               a.modele,
               (a.nb_rangees * a.largeur_rangee) AS capacite_totale,
               COALESCE(COUNT(b.id_billet), 0) AS nb_reservations
        FROM vols v
        LEFT JOIN avions a ON a.immatriculation = v.immatriculation_avion
        LEFT JOIN billets b ON b.id_vol = v.id_vol
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
    #for vol in vols:
    #    if vol.date_heure_dep_utc 
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

@admin_bp.route('/api/vols', methods=['GET'])
@admin_required
def get_vols():
    vols = db.session.execute(text("SELECT * FROM vols")).mappings().all()
    events = []
    for v in vols:
        bg_color = '#002A5C'
        if v.statut == 'retardé': bg_color = '#F57C00'
        elif v.statut == 'annulé': bg_color = '#C62828'
        elif v.statut == 'embarquement': bg_color = '#2E7D32'
        
        events.append({
            'id': v.id_vol,
            'title': f"{v.id_aeroport_depart} ✈ {v.id_aeroport_arrivee}",
            'start': v.date_heure_dep_utc.isoformat() + 'Z',
            'end': v.date_heure_arr_utc.isoformat() + 'Z' if v.date_heure_arr_utc else None,
            'backgroundColor': bg_color,
            'borderColor': '#FFC72C',
            'extendedProps': {
                'avion': v.immatriculation_avion,
                'depart': v.id_aeroport_depart,
                'arrivee': v.id_aeroport_arrivee,
                'prix': str(v.prix_de_base),
                'statut': v.statut
            }
        })
    return jsonify(events)

@admin_bp.route('/api/vols', methods=['POST'])
@admin_required
def create_vol():
    """API : Créer un nouveau vol"""
    data = request.json
    try:
        def clean_iso_date(date_str):
            if not date_str:
                return None
            return date_str.replace('Z', '').split('.')[0]
        
        start_time = datetime.fromisoformat(clean_iso_date(data['start']))
        end_time = datetime.fromisoformat(clean_iso_date(data['end']))
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
            }), 409 #code error de con
        
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
    vol = db.session.execute(text("SELECT * FROM vols WHERE id_vol = :id_vol LIMIT 1"),{"id_vol": id_vol}).mappings().all()

    if not vol:
        return jsonify({'success': False, 'message': 'Vol introuvable'}), 404
        
    try:
        def clean_iso_date(date_str):
            if not date_str:
                return None
            return date_str.replace('Z', '').split('.')[0]
        
        nouvel_avion = data.get('avion', vol.immatriculation_avion)
        nouveau_start = vol.date_heure_dep_utc
        nouveau_end = vol.date_heure_arr_utc
        
        if 'start' in data and data['start']:
            nouveau_start = datetime.fromisoformat(clean_iso_date(data['start']))
        if 'end' in data and data['end']:
            nouveau_end = datetime.fromisoformat(clean_iso_date(data['end']))
        
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
            
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/api/vols/<int:id_vol>', methods=['DELETE'])
@admin_required
def delete_vol(id_vol):
    """API : Supprimer un vol"""
    vol = Vols.query.get(id_vol)
    if not vol:
        return jsonify({'success': False, 'message': 'Vol introuvable'}), 404
    try:
        db.session.delete(vol)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400