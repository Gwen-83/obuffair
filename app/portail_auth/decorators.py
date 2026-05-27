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

def login_required(f):
    """
    Décorateur pour exiger que l'utilisateur soit connecté.
    Si non connecté → redirige vers /auth/login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Décorateur pour exiger que l'utilisateur soit admin.
    - Si non connecté → redirige vers /auth/login
    - Si connecté mais pas admin → affiche erreur 403 (Forbidden)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Vous devez être connecté pour accéder à cette page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Charger l'utilisateur depuis la BD pour vérifier son statut admin
        from app.portail_auth.models_auth import User
        user = User.query.get(session['user_id'])
        
        if not user or not user.is_admin:
            flash('Accès refusé. Seuls les administrateurs peuvent accéder à cette page.', 'danger')
            return redirect(url_for('index'))  # ou un route 403
        
        return f(*args, **kwargs)
    return decorated_function
