"""
Routes admin : CRUD vols/avions/aéroports, configuration tarifaire, dashboards analytiques.
Gère aussi les droits d'accès et logs d'audit.
"""

from flask import Blueprint, render_template

# Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
def dashboard():
    """Tableau de bord administrateur"""
    return render_template('admin/dashboard.html')
