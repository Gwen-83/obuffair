"""
Modèles SQLAlchemy pour la base de données
"""

from app import db
from datetime import datetime


class User(db.Model):
    """Modèle User - représente un client"""
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nom = db.Column(db.String(120))
    prenom = db.Column(db.String(120))
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'