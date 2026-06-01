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
    
    # Configuration cabine: nombre de rangées et largeur de chaque rangée
    nb_rangees = db.Column(db.Integer, nullable=False, default=0)
    largeur_rangee = db.Column(db.Integer, nullable=False, default=0)

    # Plages de rangées pour chaque classe
    eco_rang_de = db.Column(db.Integer, nullable=False, default=1)
    eco_rang_a = db.Column(db.Integer, nullable=False, default=1)
    bus_rang_de = db.Column(db.Integer, nullable=False, default=1)
    bus_rang_a = db.Column(db.Integer, nullable=False, default=1)
    first_rang_de = db.Column(db.Integer, nullable=False, default=1)
    first_rang_a = db.Column(db.Integer, nullable=False, default=1)
    
    # Statut de l'avion (True = actif, False = retiré de service)
    actif = db.Column(db.Boolean, default=True, nullable=False)
    
    # Dates pour l'audit
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Avion {self.immatriculation} - {self.modele}>'
    
    @property
    def eco_capacite(self):
        """Capacité classe éco"""
        if self.eco_rang_a >= self.eco_rang_de:
            return max(0, self.eco_rang_a - self.eco_rang_de + 1) * self.largeur_rangee
        return 0

    @property
    def bus_capacite(self):
        """Capacité  classe business"""
        if self.bus_rang_a >= self.bus_rang_de:
            return max(0, self.bus_rang_a - self.bus_rang_de + 1) * self.largeur_rangee
        return 0

    @property
    def first_capacite(self):
        """Capacité classe first"""
        if self.first_rang_a >= self.first_rang_de:
            return max(0, self.first_rang_a - self.first_rang_de + 1) * self.largeur_rangee
        return 0

    @property
    def capacite_totale(self):
        """Calcule la capacité totale par multiplication"""
        return max(0, self.nb_rangees) * max(0, self.largeur_rangee)

class Vols(db.Model):
    
    id_vol = db.Column(db.Integer, primary_key = True)

    immatriculation_avion = db.Column(db.String(10), nullable=False, index=True)

    id_aeroport_depart = db.Column(db.String(3), nullable=False, index=True)

    id_aeroport_arrivee = db.Column(db.String(3), nullable=False, index=True)

    date_heure_dep_utc = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    date_heure_arr_utc = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    prix_de_base = db.Column(db.Integer, nullable=False)

    statut = db.Column(db.String(20), default="à l'heure", nullable=False)

    def __repr__(self):
        return f'<Vol {self.id_vol}: {self.id_aeroport_depart} -> {self.id_aeroport_arrivee}>'

class Support(db.Model):
    """
    Modèle pour les tickets de support clients.
    Gère les demandes d'assistance et les réclamations.
    """
    __tablename__ = 'support'
    
    # ID du ticket de support (clé primaire)
    id_ticket = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Référence du client
    id_client = db.Column(db.Integer, nullable=False, index=True)
    
    # Titre/Sujet du ticket
    titre = db.Column(db.String(255), nullable=False)
    
    # Description détaillée du problème
    description = db.Column(db.Text, nullable=False)
    
    # Statut du ticket : nouveau, en cours, résolu, fermé
    statut = db.Column(db.String(20), default="nouveau", nullable=False)
    
    # Catégorie : reservation, vol, bagage, paiement, autre
    categorie = db.Column(db.String(50), default="autre", nullable=False)
    
    # Priorité : basse, normale, haute
    priorite = db.Column(db.String(20), default="normale", nullable=False)
    
    # Notes internes de l'admin
    notes_internes = db.Column(db.Text, nullable=True)
    
    # Dates
    date_creation = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Support #{self.id_ticket}: {self.titre} ({self.statut})'