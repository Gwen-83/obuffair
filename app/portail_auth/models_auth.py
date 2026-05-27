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
    # Nom de la table en BD
    __tablename__ = 'clients'
    
    # ID unique pour chaque user (auto-increment)
    id_client = db.Column(db.Integer, primary_key=True)
    
    # Email (deux users ne peuvent pas avoir le même email) index=True pour recherche rapide
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Password hashé
    mot_de_passe = db.Column(db.String(255), nullable=False)
    
    # Nom
    nom = db.Column(db.String(120), nullable=False)
    
    # Prénom
    prenom = db.Column(db.String(120), nullable=False)
    
    # Date de naissance
    date_naissance = db.Column(db.Date)
    
    # Points de fidélité (par défaut 0)
    points_fidelite = db.Column(db.Integer, default=0)
    
    # Token pour réinitialiser le mot de passe (None si pas de reset en cours)
    reset_token = db.Column(db.String(255), unique=True, nullable=True)
    
    # Expiration du token de réinitialisation
    reset_token_expiration = db.Column(db.DateTime, nullable=True)