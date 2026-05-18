"""
Routes d'authentification.

Fonctionnement:
1. GET /auth/register  → Affiche le formulaire
2. POST /auth/register → Valide et crée l'utilisateur
3. Succès → Flash + Redirection vers login
4. Erreur → Flash message + Réaffiche le formulaire
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash
from app import db
from app.portail_auth.models_auth import User
from app.portail_auth.forms import RegisterForm
from sqlalchemy.exc import IntegrityError

# Configuration du logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Enregistrement d'un nouvel utilisateur.
    
    GET: Affiche le formulaire d'inscription
    POST: Crée l'utilisateur si les données sont valides
    """
    form = RegisterForm()
    
    # Si le formulaire est soumis ET valide
    if form.validate_on_submit():
        try:
            # Préparer les données (normalisation)
            email = form.email.data.strip().lower()
            prenom = form.prenom.data.strip() if form.prenom.data else ''
            nom = form.nom.data.strip() if form.nom.data else ''
            
            # Hacher le mot de passe (méthode sécurisée)
            hashed_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256'
            )
            
            # Créer l'utilisateur
            user = User(
                email=email,
                mot_de_passe=hashed_password,
                prenom=prenom,
                nom=nom,
                date_naissance=form.date_naissance.data if form.date_naissance.data else None,
                points_fidelite=0
            )
            
            # Sauvegarder en base de données
            db.session.add(user)
            db.session.commit()
            
            # Log de succès
            logger.info(f'Nouvel utilisateur créé: {email}')
            
            # Message de succès et redirection
            flash(
                f'✓ Bienvenue {prenom}! Vous êtes inscrit avec succès. Connectez-vous maintenant.',
                'success'
            )
            return redirect(url_for('auth.login'))
        
        except IntegrityError:
            db.session.rollback()
            logger.warning(f'Tentative d\'inscription avec email existant')
            flash(
                '✗ Erreur: Cet email est déjà utilisé.',
                'danger'
            )
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de l\'inscription: {str(e)}')
            flash(
                '✗ Erreur système. Veuillez réessayer ou contacter l\'assistance.',
                'danger'
            )
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Route de connexion - À implémenter"""
    return "Page de login à venir"
