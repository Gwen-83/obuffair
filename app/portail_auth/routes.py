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
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash  # Hash et vérification password
from app import db  # Accès à la base de données
from app.model import User  # Modèle User
from app.portail_auth.forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm  # Formulaires
from app.portail_auth.email_utils import send_reset_password_email, send_verification_email  # Utilitaires pour envoyer les emails
from sqlalchemy import text
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
            
            verification_token = secrets.token_urlsafe(64)
            email_verification_expiration = datetime.utcnow() + timedelta(hours=24)
            
            user = User(
                email=email,
                mot_de_passe=hashed_password,
                prenom=prenom,
                nom=nom,
                date_naissance=form.date_naissance.data if form.date_naissance.data else None,
                points_fidelite=0,
                is_admin=False,
                email_verified=False,
                email_verification_token=verification_token,
                email_verification_token_expiration=email_verification_expiration
            )
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f'Nouvel utilisateur créé: {email}')
            
            if send_verification_email(email, verification_token, current_app):
                flash('Inscription réussie! Un email de vérification a été envoyé à votre adresse.', 'success')
                return redirect(url_for('auth.login'))
            else:
                # Si l'envoi échoue, supprimer l'utilisateur créé pour éviter un compte bloqué sans email
                db.session.delete(user)
                db.session.commit()
                logger.error(f'Erreur lors de l\'envoi de l\'email de vérification à: {email}')
                flash('Erreur lors de l\'envoi de l\'email de vérification. Inscription annulée.', 'danger')
                return render_template('auth/register.html', form=form)
        
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
            user = db.session.execute(text("SELECT * FROM clients WHERE email = :email LIMIT 1"),{"email": email}).mappings().first()
            
            if user and not user['email_verified']:
                logger.warning(f'Tentative de connexion sans email vérifié: {email}')
                flash('Veuillez vérifier votre email avant de vous connecter.', 'warning')
                return render_template('auth/login.html', form=form)
            
            # user exist + mdp correct avec hash dans bdd
            if user and check_password_hash(user['mot_de_passe'], password):
                # Auth réussi
                session['user_id'] = user['id_client']
                session['email'] = user['email']
                session['prenom'] = user['prenom']
                session['nom'] = user['nom']
                session['is_admin'] = str(user['is_admin']).lower() in ('1', 'true', 't', 'yes', 'y')
                
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
    
    return redirect(url_for('auth.login'))


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
            user = db.session.execute(
                text("SELECT * FROM clients WHERE email = :email LIMIT 1"),
                {"email": email}
            ).mappings().first()
            
            if user:
                # token 64 car
                reset_token = secrets.token_urlsafe(64)
                
                # Stocker le token et son expiration (1 heure)
                db.session.execute(
                    text("UPDATE clients SET reset_token = :reset_token, reset_token_expiration = :expiration WHERE id_client = :id"),
                    {
                        "reset_token": reset_token,
                        "expiration": datetime.utcnow() + timedelta(hours=1),
                        "id": user['id_client']
                    }
                )
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
    
    # cherche user avec token = reset token
    user = db.session.execute(text("SELECT * FROM clients WHERE reset_token = :token LIMIT 1"),{"token": token}).mappings().first()
    
    # Vérif user existe et token en vie
    if not user or user['reset_token_expiration'] < datetime.utcnow():
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
            db.session.execute(text("UPDATE clients SET mot_de_passe = :password, reset_token = NULL, reset_token_expiration = NULL WHERE id_client = :id"),{"password": hashed_password,"id": user['id_client']})
            db.session.commit()
            
            logger.info(f'Mot de passe réinitialisé pour: {user["email"]}')
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
    if 'user_id' in session:
        return redirect(url_for('client.accueil'))

    user = db.session.execute(
        text("SELECT * FROM clients WHERE email_verification_token = :token LIMIT 1"),
        {"token": token}
    ).mappings().first()

    if not user or user['email_verification_token_expiration'] < datetime.utcnow():
        logger.warning(f'Token de vérification invalide ou expiré: {token}')
        flash('Lien de vérification invalide ou expiré.', 'danger')
        return redirect(url_for('auth.register'))

    db.session.execute(
        text("UPDATE clients SET email_verified = true, email_verification_token = NULL, email_verification_token_expiration = NULL WHERE id_client = :id"),
        {"id": user['id_client']}
    )
    db.session.commit()

    logger.info(f"Email vérifié pour: {user['email']}")
    flash('Email vérifié avec succès! Vous pouvez vous connecter.', 'success')
    return redirect(url_for('auth.login'))


