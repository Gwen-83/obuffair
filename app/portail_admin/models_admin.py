"""
Modèles SQLAlchemy pour l'administration : avions, aéroports, vols, configuration tarifaire.

Stockage de :
- Flotte d'avions (immatriculation, modèle, capacités par classe)
- Aéroports et infrastructures
- Configuration de tarification
- Logs d'audit des actions admin
"""

from app import db
from datetime import datetime


class Avion(db.Model):
    """
    Représente un avion de la flotte.
    Chaque avion est unique par son immatriculation.
    """
    __tablename__ = 'avions'
    
    # Clé primaire
    id_avion = db.Column(db.Integer, primary_key=True)
    
    # Immatriculation unique (ex: F-GKXN)
    immatriculation = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Modèle de l'avion (ex: Boeing 787, Airbus A350)
    modele = db.Column(db.String(50), nullable=False)
    
    # Numéro de série du constructeur
    numero_serie = db.Column(db.String(50), nullable=True)
    
    # Capacités par classe de cabine
    capacite_eco = db.Column(db.Integer, nullable=False, default=0)
    capacite_premium = db.Column(db.Integer, nullable=False, default=0)  # Business/Premium economy
    capacite_first = db.Column(db.Integer, nullable=False, default=0)
    
    # Statut de l'avion
    # Valeurs possibles: 'actif', 'maintenance', 'retiré'
    statut = db.Column(db.String(20), nullable=False, default='actif')
    
    # Dates
    date_acquisition = db.Column(db.Date, nullable=True)
    date_derniere_maintenance = db.Column(db.DateTime, nullable=True)
    
    # Métadonnées
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Avion {self.immatriculation} - {self.modele}>'
    
    @property
    def capacite_totale(self):
        """Calcule la capacité totale en sièges"""
        return self.capacite_eco + self.capacite_premium + self.capacite_first
    
    def to_dict(self):
        """Sérialise l'avion en dictionnaire pour JSON"""
        return {
            'id_avion': self.id_avion,
            'immatriculation': self.immatriculation,
            'modele': self.modele,
            'numero_serie': self.numero_serie,
            'capacite_eco': self.capacite_eco,
            'capacite_premium': self.capacite_premium,
            'capacite_first': self.capacite_first,
            'capacite_totale': self.capacite_totale,
            'statut': self.statut,
            'date_acquisition': self.date_acquisition.isoformat() if self.date_acquisition else None,
            'date_derniere_maintenance': self.date_derniere_maintenance.isoformat() if self.date_derniere_maintenance else None,
        }