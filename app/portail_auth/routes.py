"""
Routes d'authentification.

Fonctionnement:
1. GET /auth/register  → Affiche le formulaire
2. POST /auth/register → Valide et crée l'utilisateur
3. Succès → Flash + Redirection vers login
4. Erreur → Flash message + Réaffiche le formulaire
"""

import logging  # Pour afficher des logs
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash  # Hash et vérification password
from app import db  # Accès à la base de données
from app.portail_auth.models_auth import User  # Modèle User
from app.portail_auth.forms import RegisterForm, LoginForm  # Formulaires
from sqlalchemy.exc import IntegrityError  # Exception si email dupliqué en BD

# Créer un log pour afficher des messages lors du debug
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Créer un "blueprint" (un mini-app) pour les routes d'auth
# Toutes les routes commenceront par /auth
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])  # Accepter GET/ POST
def register():
    """
    La route pour l'inscription.
    GET = on affiche le formulaire vide
    POST = l'utilisateur soumet, on crée le compte
    """
    # Créer une instance du formulaire
    form = RegisterForm()
    
    # formulaire soumis (POST)
    # validateurs okay
    if form.validate_on_submit():
        try:
            # Nettoyer les data
            email = form.email.data.strip().lower()
            prenom = form.prenom.data.strip() if form.prenom.data else ''
            nom = form.nom.data.strip() if form.nom.data else ''
            
            # Hacher password avec SHA256
            hashed_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256'
            )
            
            # Créer un nouvel objet User avec données formulaire
            user = User(
                email=email,
                mot_de_passe=hashed_password,
                prenom=prenom,
                nom=nom,
                date_naissance=form.date_naissance.data if form.date_naissance.data else None,
                points_fidelite=0
            )
            
            db.session.add(user)
            db.session.commit()
            
            # Log pour le debug
            logger.info(f'Nouvel utilisateur créé: {email}')
            
            # Afficher un message succès à l'user
            flash(
                f'✓ Bienvenue {prenom}! Vous êtes inscrit avec succès. Connectez-vous maintenant.',
                'success'
            )

            return redirect(url_for('auth.login'))
        
        except IntegrityError:
            # IntegrityError si email déjà existant au cas ou validator précédent a loupé
            db.session.rollback()
            logger.warning(f'Tentative d\'inscription avec email existant')
            flash(
                '✗ Erreur: Cet email est déjà utilisé.',
                'danger'
            )
        
        except Exception as e:
            # Toutes les autres erreurs non prévues
            db.session.rollback()
            logger.error(f'Erreur lors de l\'inscription: {str(e)}')
            flash(
                '✗ Erreur système. Veuillez réessayer ou contacter l\'assistance.',
                'danger'
            )
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    La route pour la connexion.
    GET = on affiche le formulaire vide
    POST = l'utilisateur soumet, on vérifie ses identifiants
    """
    # Si déjà connecté, rediriger vers le portail client
    if 'user_id' in session:
        return redirect(url_for('client.accueil'))
    
    # Créer une instance du formulaire
    form = LoginForm()
    
    # Formulaire soumis (POST) et validé
    if form.validate_on_submit():
        try:
            # Nettoyer l'email
            email = form.email.data.strip().lower()
            password = form.password.data
            
            # Chercher l'utilisateur par email
            user = User.query.filter_by(email=email).first()
            
            # Vérifier que l'utilisateur existe ET que le mot de passe est correct
            if user and check_password_hash(user.mot_de_passe, password):
                # Authentification réussie
                session['user_id'] = user.id_client
                session['email'] = user.email
                session['prenom'] = user.prenom
                session['nom'] = user.nom
                
                logger.info(f'Utilisateur connecté: {email}')
                flash(
                    f'✓ Bienvenue {user.prenom}! Vous êtes connecté avec succès.',
                    'success'
                )
                
                # Rediriger vers le portail client
                return redirect(url_for('client.accueil'))
            else:
                # Authentification échouée
                logger.warning(f'Tentative de connexion échouée pour: {email}')
                flash(
                    '✗ Email ou mot de passe incorrect.',
                    'danger'
                )
        
        except Exception as e:
            # Erreur système
            logger.error(f'Erreur lors de la connexion: {str(e)}')
            flash(
                '✗ Erreur système. Veuillez réessayer ou contacter l\'assistance.',
                'danger'
            )
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    """
    Route pour la déconnexion.
    Supprime les données de session et redirige vers la page d'accueil.
    """
    if 'user_id' in session:
        prenom = session.get('prenom', 'Utilisateur')
        session.clear()
        logger.info(f'Utilisateur déconnecté: {prenom}')
        flash(
            f'✓ À bientôt {prenom}! Vous êtes maintenant déconnecté.',
            'success'
        )
    
    return redirect(url_for('index'))
