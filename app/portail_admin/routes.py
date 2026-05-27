"""
Routes admin : CRUD vols/avions/aéroports, configuration tarifaire, dashboards analytiques.
Gère aussi les droits d'accès et logs d'audit.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.portail_auth.decorators import admin_required
from app import db
from app.portail_admin.modele_admin import Avion
from app.portail_admin.forms import FormAjouterAvion
from app.portail_admin.modele_admin import Vols
# Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    nb_vols = db.session.execute(db.text("SELECT COUNT(*) FROM vols ")).fetchone()
    return render_template('admin/html/dashboard.html', nb_vols=nb_vols)


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
    avions = Avion.query.all()
    
    # Formulaire ajout avins
    if form.validate_on_submit():
        # Unicité immat
        immat_upper = form.immatriculation.data.upper() if form.immatriculation.data else ''
        avion_existant = Avion.query.filter_by(immatriculation=immat_upper).first()
        if avion_existant:
            flash('Cette immatriculation existe déjà', 'danger')
        else:
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
                flash(f'Avion {nouvel_avion.immatriculation} ajouté avec succès', 'success')
                return redirect(url_for('admin.config_avion'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de l\'ajout : {str(e)}', 'danger')
    
    return render_template('admin/html/config_avion.html', avions=avions, form=form)

@admin_bp.route('/api/avion/<string:immatriculation>', methods=['DELETE'])
@admin_required
def supprimer_avion(immatriculation):
    """supprimer avion en désactivant"""
    avion = Avion.query.get_or_404(immatriculation)
    try:
        avion.actif = False
        db.session.commit()
        return jsonify({'success': True, 'message': f'Avion {avion.immatriculation} supprimé'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/api/avions', methods=['GET'])
@admin_required
def get_avions_json():
    """Avions liste en JSON"""
    filtre_actif = request.args.get('actif', 'true').lower() == 'true'
    avions = Avion.query.filter_by(actif=filtre_actif).all() if filtre_actif else Avion.query.all()
    
    return jsonify([{
        'immatriculation': a.immatriculation,
        'modele': a.modele,
        'eco_capacite': a.eco_capacite,
        'bus_capacite': a.bus_capacite,
        'first_capacite': a.first_capacite,
        'nb_rangees': a.nb_rangees,
        'largeur_rangee': a.largeur_rangee,
        'eco_rang_de': a.eco_rang_de,
        'eco_rang_a': a.eco_rang_a,
        'bus_rang_de': a.bus_rang_de,
        'bus_rang_a': a.bus_rang_a,
        'first_rang_de': a.first_rang_de,
        'first_rang_a': a.first_rang_a,
        'capacite_totale': a.capacite_totale,
        'actif': a.actif
    } for a in avions])


@admin_bp.route('/api/avion/<string:immatriculation>', methods=['GET'])
@admin_required
def get_avion_json(immatriculation):
    a = Avion.query.get_or_404(immatriculation)
    return jsonify({
        'immatriculation': a.immatriculation,
        'modele': a.modele,
        'eco_capacite': a.eco_capacite,
        'bus_capacite': a.bus_capacite,
        'first_capacite': a.first_capacite,
        'nb_rangees': a.nb_rangees,
        'largeur_rangee': a.largeur_rangee,
        'eco_rang_de': a.eco_rang_de,
        'eco_rang_a': a.eco_rang_a,
        'bus_rang_de': a.bus_rang_de,
        'bus_rang_a': a.bus_rang_a,
        'first_rang_de': a.first_rang_de,
        'first_rang_a': a.first_rang_a,
        'capacite_totale': a.capacite_totale,
        'actif': a.actif
    })


@admin_bp.route('/avion/<string:immatriculation>/edit', methods=['GET', 'POST'])
@admin_required
def edit_avion(immatriculation):
    """Modifier un avion existant"""
    avion = Avion.query.get_or_404(immatriculation)
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
            # On n'autorise pas le changement d'immatriculation primaire
            avion.modele = form.modele.data or ''
            avion.nb_rangees = form.nb_rangees.data or 0
            avion.largeur_rangee = form.largeur_rangee.data or 0
            avion.eco_rang_de = form.eco_rang_de.data or 0
            avion.eco_rang_a = form.eco_rang_a.data or 0
            avion.bus_rang_de = form.bus_rang_de.data or 0
            avion.bus_rang_a = form.bus_rang_a.data or 0
            avion.first_rang_de = form.first_rang_de.data or 0
            avion.first_rang_a = form.first_rang_a.data or 0
            avion.actif = form.actif.data if form.actif.data is not None else True
            db.session.commit()
            flash(f'Avion {avion.immatriculation} modifié', 'success')
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
