"""
Modèles SQLAlchemy pour la base de données.

Stockage sécurisé des utilisateurs avec:
- Passwords hashés (PBKDF2-SHA256)
- Emails normalisés en minuscules
- Intégration avec table clients existante
- Tokens de réinitialisation de mot de passe sécurisés
"""

from app import db  # Instance SQLAlchemy pour accéder à la BD
from datetime import datetime, timedelta  # Pour gérer l'expiration des tokens

class User(db.Model):
    """
    C'est la structure de la table 'clients' en BD.
    Chaque instance User = une ligne dans la table.
    """
    __tablename__ = 'clients'
    
    # ID chaque user
    id_client = db.Column(db.Integer, primary_key=True)
    
    # Email (deux users ne peuvent pas avoir le même email)/ index=True pour recherche rapide
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Password hashé
    mot_de_passe = db.Column(db.String(255), nullable=False)
    
    # Nom
    nom = db.Column(db.String(100), nullable=False)
    
    # Prénom
    prenom = db.Column(db.String(100), nullable=False)
    
    # Date de naissance
    date_naissance = db.Column(db.Date)
    
    # Points de fidélité
    points_fidelite = db.Column(db.Integer, default=0)
    
    # Token pour réinitialiser le mot de passe
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    
    # Expiration du token de réinitialisation
    reset_token_expiration = db.Column(db.DateTime, nullable=True)
    
    # Booléen pour vérifier si l'email est confirmé
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Token pour vérifier l'email
    email_verification_token = db.Column(db.String(255), unique=True, nullable=True)
    
    # Expiration du token de vérification d'email
    email_verification_token_expiration = db.Column(db.DateTime, nullable=True)
    
    # Booléen pour indiquer si l'utilisateur est administrateur
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    __table_args__ = {'extend_existing': True}
    id_reservation = db.Column(db.Integer, primary_key = True)