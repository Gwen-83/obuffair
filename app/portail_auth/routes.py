"""
Routes d'authentification : login, register, logout, password recovery, email confirmation.
Gère les redirects et messages flash selon l'état de session.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from app import db
from obuffair.app.portail_auth.models_auth import User
from app.portail_auth.forms import RegisterForm

# blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Route d'enregistrement"""
    form = RegisterForm()
    
    if form.validate_on_submit():
        try:
            # Créer nouvel utilisateur
            hashed_password = generate_password_hash(form.password.data)
            user = User(
                email=form.email.data,
                username=form.username.data,
                password=hashed_password,
                prenom=form.prenom.data,
                nom=form.nom.data
            )
            
            # Ajouter à la base de données
            db.session.add(user)
            db.session.commit()
            
            flash(f'Bienvenue {form.username.data}! Vous êtes inscrit avec succès!', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'inscription: {str(e)}', 'danger')
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Route de connexion"""
    return "Page de login à venir"
