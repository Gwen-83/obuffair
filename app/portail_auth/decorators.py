"""
Décorateurs pour protéger les routes en fonction du rôle de l'utilisateur.

Utilisation:
- @login_required : L'utilisateur DOIT être connecté
- @admin_required : L'utilisateur DOIT être connecté ET admin
- Sans décorateur : Route accessible à tous (public)

Exemple:
    @app.route('/mon-route')
    @login_required
    def ma_route():
        return "Accessible seulement si connecté"
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from app import db
from sqlalchemy import text

def _is_truthy(value):
    """Gère le type bit(1) de MySQL qui retourne des bytes"""
    if isinstance(value, (bytes, bytearray)):
        return any(b != 0 for b in value)
    return str(value).lower() in ('1', 'true', 't', 'yes', 'y')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = db.session.execute(
            text("SELECT is_admin FROM clients WHERE id_client = :id LIMIT 1"),
            {"id": session['user_id']}
        ).mappings().first()
        
        if not user or not _is_truthy(user['is_admin']):
            flash('Accès refusé. Seuls les administrateurs peuvent accéder à cette page.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function
