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
from app.portail_auth.email_utils import send_reset_password_email, send_verification_email  # Utilitaires pour envoyer les emails
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
    if 'user_id' in session:
        return redirect(url_for('client.accueil'))
    
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
            
            # Générer un token de vérification d'email (64 caractères sécurisés)
            verification_token = secrets.token_urlsafe(64)
            
            user = User(
                email=email,
                mot_de_passe=hashed_password,
                prenom=prenom,
                nom=nom,
                date_naissance=form.date_naissance.data if form.date_naissance.data else None,
                points_fidelite=0,
                email_verified=False,
                email_verification_token=verification_token,
                email_verification_token_expiration=datetime.utcnow() + timedelta(hours=24)
            )
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f'Nouvel utilisateur créé: {email}')
            
            # Envoyer l'email de vérification
            from flask import current_app
            if send_verification_email(email, verification_token, current_app):
                flash('Inscription réussie! Un email de vérification a été envoyé à votre adresse.', 'success')
                logger.info(f'Email de vérification envoyé à: {email}')
            else:
                flash('Inscription réussie mais erreur lors de l\'envoi de l\'email. Vérifiez votre boîte mail.', 'warning')
                logger.error(f'Erreur lors de l\'envoi de l\'email de vérification à: {email}')

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
            
            # Vérifier que l'email est confirmé (avant de vérifier le mot de passe)
            if user and not user.email_verified:
                logger.warning(f'Tentative de connexion avec email non vérifié: {email}')
                flash('Veuillez vérifier votre email avant de vous connecter.', 'warning')
                return render_template('auth/login.html', form=form)
            
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
                flash('Email ou mot de passe incorrect.','danger')
        
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
    POST = génère un token et envoie un email avec le lien de réinitialisation
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
                
                # Stocker le token et son expiration (1 heure)
                user.reset_token = reset_token
                user.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
                
                db.session.commit()
                
                logger.info(f'Token de réinitialisation généré pour: {email}')
                
                # Envoyer l'email avec le lien de réinitialisation
                from flask import current_app
                if send_reset_password_email(email, reset_token, current_app):
                    flash('Un email de réinitialisation a été envoyé à votre adresse email.', 'success')
                    logger.info(f'Email de réinitialisation envoyé à: {email}')
                else:
                    flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer.', 'danger')
                    logger.error(f'Erreur lors de l\'envoi d\'email à: {email}')
                
                # Rediriger vers login (même si l'email n'existe pas, pour des raisons de sécurité)
                return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la réinitialisation: {str(e)}')
            flash('Erreur du système','danger')
    
    return render_template('auth/forgot_password.html', form=form)


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
    if not user or user.reset_token_expiration < datetime.utcnow():
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


@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """
    Route pour vérifier l'email avec un token.
    Généré lors de l'inscription, permet de confirmer l'adresse email.
    """
    # Cherche user avec le token de vérification
    user = User.query.filter_by(email_verification_token=token).first()
    
    # Vérif user existe et token en vie
    if not user or user.email_verification_token_expiration < datetime.utcnow():
        logger.warning(f'Token de vérification invalide ou expiré: {token}')
        flash('Lien de vérification invalide ou expiré. Veuillez vous réinscrire.', 'danger')
        return redirect(url_for('auth.register'))
    
    # Vérifier l'email et supprimer le token
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_token_expiration = None
    
    db.session.commit()
    
    logger.info(f'Email vérifié pour: {user.email}')
    flash('Email vérifié avec succès! Vous pouvez vous connecter.', 'success')
    
    return redirect(url_for('auth.login'))
