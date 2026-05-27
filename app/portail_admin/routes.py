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
        avion_existant = Avion.query.filter_by(immatriculation=form.immatriculation.data.upper()).first()
        if avion_existant:
            flash('Cette immatriculation existe déjà', 'danger')
        else:
            try:
                nouvel_avion = Avion(
                    immatriculation=form.immatriculation.data.upper(),
                    modele=form.modele.data,
                    capacite_eco=form.capacite_eco.data,
                    capacite_business=form.capacite_business.data,
                    capacite_first=form.capacite_first.data,
                    actif=form.actif.data
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
        'capacite_eco': a.capacite_eco,
        'capacite_business': a.capacite_business,
        'capacite_first': a.capacite_first,
        'capacite_totale': a.capacite_totale,
        'actif': a.actif
    } for a in avions])

@admin_bp.route('/infrastructure')
@admin_required
def infrastructure_aeroportuaire():
    """infrastructure des aéroports desservis"""
    return render_template('admin/html/infrastructure.html')
