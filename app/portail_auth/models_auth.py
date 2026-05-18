"""
Modèles SQLAlchemy pour la base de données.

Stockage sécurisé des utilisateurs avec:
- Passwords hashés (PBKDF2-SHA256)
- Emails normalisés en minuscules
- Intégration avec table clients existante
"""

from app import db
from datetime import datetime


class User(db.Model):
    """
    Modèle User - représente un client/utilisateur.
    
    Correspond à la table clients réelle avec:
    - id_client: Identifiant unique
    - email: Email unique (minuscules)
    - mot_de_passe: Mot de passe hashé (jamais stocké en clair!)
    - nom: Nom de famille
    - prenom: Prénom
    - date_naissance: Date de naissance
    - points_fidelite: Points de fidélité (défaut: 0)
    """
    __tablename__ = 'clients'
    
    id_client = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    mot_de_passe = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(120), nullable=False)
    prenom = db.Column(db.String(120), nullable=False)
    date_naissance = db.Column(db.Date)
    points_fidelite = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<User: {self.prenom} {self.nom} ({self.email})>'
    
    def get_nom_complet(self):
        """Retourne le nom complet (prénom + nom)"""
        if self.prenom and self.nom:
            return f'{self.prenom} {self.nom}'
        return self.prenom or self.nom or self.email