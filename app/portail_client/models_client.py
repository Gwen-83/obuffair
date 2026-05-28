"""
Modèles SQLAlchemy pour le portail client.
Contient les tables liées aux vols, aéroports, avions, réservations et billets.
"""

from app import db
from datetime import datetime

class Aeroport(db.Model):
    __tablename__ = 'aeroports'
    id_aeroport = db.Column(db.String(3), primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    ville = db.Column(db.String(100), nullable=False)
    pays = db.Column(db.String(100), nullable=False)
    decalage_utc = db.Column(db.Numeric(4, 2), nullable=False, default=0.00)

    # --- Relations ---
    vols_depart = db.relationship('Vol', foreign_keys='Vol.id_aeroport_depart', back_populates='aeroport_depart', lazy=True)
    vols_arrivee = db.relationship('Vol', foreign_keys='Vol.id_aeroport_arrivee', back_populates='aeroport_arrivee', lazy=True)

class Avion(db.Model):
    __tablename__ = 'avions'
    immatriculation = db.Column(db.String(10), primary_key=True)
    modele = db.Column(db.String(50), nullable=False)
    capacite_eco = db.Column(db.Integer, nullable=False)
    capacite_business = db.Column(db.Integer, nullable=False)
    capacite_first = db.Column(db.Integer, nullable=False)
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, nullable=True)

    # --- Relations ---
    vols = db.relationship('Vol', back_populates='avion', lazy=True)

class Vol(db.Model):
    __tablename__ = 'vols'
    id_vol = db.Column(db.Integer, primary_key=True)
    immatriculation_avion = db.Column(db.String(10), db.ForeignKey('avions.immatriculation'), nullable=False)
    id_aeroport_depart = db.Column(db.String(3), db.ForeignKey('aeroports.id_aeroport'), nullable=False)
    id_aeroport_arrivee = db.Column(db.String(3), db.ForeignKey('aeroports.id_aeroport'), nullable=False)
    date_heure_dep_utc = db.Column(db.DateTime, nullable=False)
    date_heure_arr_utc = db.Column(db.DateTime, nullable=False)
    prix_de_base = db.Column(db.Numeric(10, 2), nullable=False)

    # --- Relations ---
    avion = db.relationship('Avion', back_populates='vols')
    aeroport_depart = db.relationship('Aeroport', foreign_keys=[id_aeroport_depart], back_populates='vols_depart')
    aeroport_arrivee = db.relationship('Aeroport', foreign_keys=[id_aeroport_arrivee], back_populates='vols_arrivee')
    billets = db.relationship('Billet', back_populates='vol', lazy=True)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id_reservation = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer, db.ForeignKey('clients.id_client'), nullable=False)
    date_reservation = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.Enum('Confirmee', 'Annulee', 'En cours', 'En modification', 'Erreur'), default='Confirmee')

    # --- Relations ---
    client = db.relationship('User', backref=db.backref('reservations', lazy='dynamic'))
    billets = db.relationship('Billet', back_populates='reservation', lazy=True, cascade="all, delete-orphan")

class Billet(db.Model):
    __tablename__ = 'billets'
    id_billet = db.Column(db.Integer, primary_key=True)
    id_reservation = db.Column(db.Integer, db.ForeignKey('reservations.id_reservation'), nullable=False)
    id_vol = db.Column(db.Integer, db.ForeignKey('vols.id_vol'), nullable=False)
    classe = db.Column(db.Enum('Eco', 'Business', 'First'), nullable=False, default='Eco')
    options_repas = db.Column(db.Boolean, default=False)
    bagages_sup = db.Column(db.Integer, default=0)

    # --- Relations ---
    reservation = db.relationship('Reservation', back_populates='billets')
    vol = db.relationship('Vol', back_populates='billets')