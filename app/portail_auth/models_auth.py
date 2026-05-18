"""
Modèles SQLAlchemy pour la base de données.

Stockage sécurisé des utilisateurs avec:
- Passwords hashés (PBKDF2-SHA256)
- Usernames/emails normalisés en minuscules
- Timestamps automatiques
"""

from app import db
from datetime import datetime


class User(db.Model):
    """
    Modèle User - représente un client/utilisateur.
    
    Attributes:
        id: Identifiant unique
        email: Email unique (minuscules)
        username: Username unique (minuscules, 3-20 caractères)
        password: Mot de passe hashé (jamais stocké en clair!)
        nom: Nom de famille
        prenom: Prénom
        date_inscription: Timestamp de création
    """
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(120))
    prenom = db.Column(db.String(120))
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<User: {self.username} ({self.email})>'
    
    def get_nom_complet(self):
        """Retourne le nom complet (prénom + nom)"""
        if self.prenom and self.nom:
            return f'{self.prenom} {self.nom}'
        return self.prenom or self.nom or self.username