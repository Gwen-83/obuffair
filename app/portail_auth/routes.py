"""
Routes d'authentification.

Fonctionnement:
1. GET /auth/register  → Affiche le formulaire
2. POST /auth/register → Valide et crée l'utilisateur
3. Succès → Flash + Redirection vers login
4. Erreur → Flash message + Réaffiche le formulaire
"""

import logging  # Pour afficher des logs
import secrets  # Pour générer des tokens sécurisés
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import generate_password_hash, check_password_hash  # Hash et vérification password
from app import db  # Accès à la base de données
from app.portail_auth.models_auth import User  # Modèle User
from app.portail_auth.forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm  # Formulaires
from sqlalchemy.exc import IntegrityError  # Exception si email dupliqué en BD

# Créer un log pour afficher des messages lors du debug
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Créer un "blueprint" (un mini-app) pour les routes d'auth
# Toutes les routes commenceront par /auth
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    La route pour l'inscription.
    GET = on affiche le formulaire vide
    POST = l'utilisateur soumet, on crée le compte
    """
    form = RegisterForm()
    
    # validateurs okay
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            prenom = form.prenom.data.strip() if form.prenom.data else ''
            nom = form.nom.data.strip() if form.nom.data else ''
            
            hashed_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256'
            )
            
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
            
            logger.info(f'Nouvel utilisateur créé: {email}')
            
            flash(f'Inscription réussi. Connectez-vous maintenant.','success')

            return redirect(url_for('auth.login'))
        
        except IntegrityError:
            db.session.rollback()
            logger.warning(f'Tentative d\'inscription avec email existant')
            flash('email déjà existant','danger')
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de l\'inscription: {str(e)}')
            flash('Erreur du système lors de l\'inscription','danger')
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    La route pour la connexion.
    GET = on affiche le formulaire vide
    POST = l'utilisateur soumet, on vérifie ses identifiants
    """
    if 'user_id' in session:
        return redirect(url_for('client.accueil'))

    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            password = form.password.data
            
            # cherche user par email
            user = User.query.filter_by(email=email).first()
            
            # user exist + mdp correct avec hash dans bdd
            if user and check_password_hash(user.mot_de_passe, password):
                # Auth réussi
                session['user_id'] = user.id_client
                session['email'] = user.email
                session['prenom'] = user.prenom
                session['nom'] = user.nom
                
                logger.info(f'Utilisateur connecté: {email}')
                flash(f'Connexion réussie','success')
                
                # redir après auth
                return redirect(url_for('client.accueil'))
            else:
                # echec auth
                logger.warning(f'Echec de connexion: {email}')
                flash('Email ou mot de passe incorrect.')
        
        except Exception as e:
            # Erreur sys
            logger.error(f'Erreur lors de la connexion: {str(e)}')
            flash('Erreur du système lors de la connexion','danger')
    
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
        flash(f'Déconnexion effectué','success')
        logger.info(f'Utilisateur déconnecté : {prenom}')
    
    return redirect(url_for('index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Route pour demander la réinitialisation du mot de passe.
    GET = affiche le formulaire
    POST = génère un token et l'affiche en dev (en prod, il faudrait l'envoyer par email)
    """
    if 'user_id' in session:
        return redirect(url_for('client.accueil'))
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            user = User.query.filter_by(email=email).first()
            
            if user:
                # token 64 car
                reset_token = secrets.token_urlsafe(64)
                
                # Expiration
                user.reset_token = reset_token
                user.reset_token_expiration = datetime.now(datetime.timezone.utc) + timedelta(minutes=15)
                
                db.session.commit()
                
                logger.info(f'Token de réinitialisation généré pour: {email}')
                
                # dev = affichage du token a changer par envoi de mail en prod
                reset_link = url_for('auth.reset_password', token=reset_token, _external=True)
                
                flash(f'Cliquez <a href="{reset_link}">ici</a> pour réinitialiser votre mot de passe.','success')
                
                logger.info(f'Lien de réinitialisation: {reset_link}')
                
                return render_template('auth/forgot_password.html', 
                                     form=form, 
                                     reset_link=reset_link,
                                     message_affiche=True)
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la réinitialisation: {str(e)}')
            flash('Erreur du système','danger')
    
    return render_template('auth/forgot_password.html', form=form, message_affiche=False)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Route pour réinitialiser le mot de passe avec un token.
    GET = affiche le formulaire
    POST = met à jour le password et le token
    """
    if 'user_id' in session:
        return redirect(url_for('client.accueil'))
    
    # cheche user avec token = reset token
    user = User.query.filter_by(reset_token=token).first()
    
    # Vérif user existe et token en vie
    if not user or user.reset_token_expiration < datetime.now(datetime.timezone.utc):
        logger.warning(f'Token invalide ou expiré: {token}')
        flash('Lien de réinitialisation invalide ou expiré', 'danger')
        return redirect(url_for('auth.login'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        try:
            # Hacher new mdp
            hashed_password = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256'
            )
            
            # Maj mdp et del token
            user.mot_de_passe = hashed_password
            user.reset_token = None
            user.reset_token_expiration = None
            
            db.session.commit()
            
            logger.info(f'Mot de passe réinitialisé pour: {user.email}')
            flash('Mot de passe réinitialisé avec succès. Connectez-vous.', 'success')
            
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la réinitialisation: {str(e)}')
            flash('Erreur du système','danger')
    
    return render_template('auth/reset_password.html', form=form)
