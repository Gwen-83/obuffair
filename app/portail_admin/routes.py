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
# Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    nb_vols = db.session.execute(db.text("SELECT COUNT(*) FROM vols ")).fetchone()
    nb_resa = db.session.execute(db.text("SELECT COUNT(*) FROM reservations ")).fetchone()
    # Récupérer vols + modèle avion + capacité totale et nombre de réservations par vol
    vols_rows = db.session.execute(text("""
        SELECT v.*, a.modele AS modele, a.immatriculation AS immatriculation_avion,
               (a.nb_rangees * a.largeur_rangee) AS capacite_totale,
               COALESCE(r.cnt, 0) AS nb_reservations
        FROM vols v
        LEFT JOIN avions a ON v.immatriculation = a.immatriculation
        LEFT JOIN (
            SELECT id_vol, COUNT(*) AS cnt FROM reservations GROUP BY id_vol
        ) r ON r.id_vol = v.id_vol
    """)).mappings().all()

    # Calculer le pourcentage de remplissage par vol
    vols = []
    for row in vols_rows:
        d = dict(row)
        capacite = d.get('capacite_totale') or 0
        nb_resa_vol = d.get('nb_reservations') or 0
        if capacite:
            try:
                fill_percent = int((nb_resa_vol / capacite) * 100)
            except Exception:
                fill_percent = 0
        else:
            fill_percent = 0
        d['fill_percent'] = min(100, max(0, fill_percent))
        vols.append(d)
    #for vol in vols:
    #    if vol.date_heure_dep_utc 
    return render_template('admin/html/dashboard.html', nb_vols=nb_vols, nb_resa=nb_resa, vols=vols)


@admin_bp.route('/gestion_flotte')
@admin_required
def gestion_flotte():
    """gestion de flotte"""
    return render_template('admin/html/flotte.html')

@admin_bp.route('/config_avion', methods=['GET', 'POST'])
@admin_required
def config_avion():
    """Configuration des cabines et gestion de la flotte d'avions"""
    form = FormAjouterAvion()
    
    # Récupérer tous les avions
    avions = db.session.execute(text("""SELECT *,(nb_rangees * largeur_rangee) AS capacite_totale FROM avions""")).mappings().all()
    
    # Formulaire ajout avins
    if form.validate_on_submit():
        # Unicité immat
        immat_upper = form.immatriculation.data.upper() if form.immatriculation.data else ''
        avion_existant = db.session.execute(db.text("SELECT * FROM avions WHERE immatriculation = {immat_upper} LIMIT 1")).mappings().first()
        if avion_existant:
            flash('Cette immatriculation existe déjà', 'danger')
        else:
            try:
                #Nouvel avions à partir de model_amdin.py
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
    """supprimer avion en désactivant"""
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
        # Pré-remplir le formulaire
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

@admin_bp.route('/infrastructure')
@admin_required
def infrastructure_aeroportuaire():
    """infrastructure des aéroports desservis"""
    return render_template('admin/html/infrastructure.html')
