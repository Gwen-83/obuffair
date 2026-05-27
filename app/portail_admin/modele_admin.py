"""
Modèles SQLAlchemy pour la gestion administrative.

Gestion complète de la flotte d'avions avec:
- Configuration des cabines (économique, business, first)
- Suivi des avions actifs/inactifs
- Audit avec timestamps
"""

from app import db
from datetime import datetime

class Avion(db.Model):
    """
    Modèle de gestion des avions de la flotte.
    Chaque instance = une ligne dans la table 'avions'.
    """
    __tablename__ = 'avions'
    
    # Immatriculation de l'avion (clé primaire, ex: F-ABCD)
    immatriculation = db.Column(db.String(10), primary_key=True, nullable=False)
    
    # Modèle de l'avion (ex: Boeing 737, Airbus A320)
    modele = db.Column(db.String(50), nullable=False)
    
    # Capacité en classe économique
    capacite_eco = db.Column(db.Integer, nullable=False)
    
    # Capacité en classe business
    capacite_business = db.Column(db.Integer, nullable=False)
    
    # Capacité en classe first
    capacite_first = db.Column(db.Integer, nullable=False)
    
    # Statut de l'avion (True = actif, False = retiré de service)
    actif = db.Column(db.Boolean, default=True, nullable=False)
    
    # Dates pour l'audit
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Avion {self.immatriculation} - {self.modele}>'
    
    @property
    def capacite_totale(self):
        """Calcule la capacité totale de l'avion"""
        return self.capacite_eco + self.capacite_business + self.capacite_first

class Vols(db.Model):
    
    id_vol = db.Column(db.Integer, primary_key = True)

    immatriculation_avion = db.Column(db.String(10), unique=True, nullable=False, index=True)

    id_aeroport_depart = db.Column(db.String(3), unique=True, nullable=False, index=True)

    id_aeroport_arrivee = db.Column(db.String(3), unique=True, nullable=False, index=True)

    date_heure_dep_utc = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    date_heure_arr_utc = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    prix_de_base = db.Column(db.Integer, nullable=False)