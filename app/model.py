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
    __table_args__ = {'extend_existing': True}
    
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
    __tablename__ = 'vols'
    __table_args__ = {'extend_existing': True}
    
    id_vol = db.Column(db.Integer, primary_key = True)

    immatriculation_avion = db.Column(db.String(10), nullable=False, index=True)

    id_aeroport_depart = db.Column(db.String(3), nullable=False, index=True)

    id_aeroport_arrivee = db.Column(db.String(3), nullable=False, index=True)

    date_heure_dep_utc = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    date_heure_arr_utc = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    prix_de_base = db.Column(db.Integer, nullable=False)

    statut = db.Column(db.String(20), default="à l'heure", nullable=False)

    # --- Relations ---
    billets = db.relationship('Billet', back_populates='vol', lazy=True)

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


class Aeroport(db.Model):
    """
    Modèle pour les aéroports gérés par la compagnie.
    """
    __tablename__ = 'aeroports'
    __table_args__ = {'extend_existing': True}

    id_aeroport = db.Column(db.String(4), primary_key=True, nullable=False)
    nom = db.Column(db.String(120), nullable=False)
    ville = db.Column(db.String(100), nullable=False)
    pays = db.Column(db.String(100), nullable=False)
    decalage_utc = db.Column(db.String(10), nullable=False, default='+00:00')
    latitude = db.Column(db.String(50), nullable=True)
    longitude = db.Column(db.String(50), nullable=True)
    terminals_count = db.Column(db.Integer, nullable=False, default=0)
    gates_total = db.Column(db.Integer, nullable=False, default=0)
    lounges_count = db.Column(db.Integer, nullable=False, default=0)
    parkings_count = db.Column(db.Integer, nullable=False, default=0)
    services = db.Column(db.Text, nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_email = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Aéroport {self.id_aeroport} - {self.nom}>'

"""
Modèles SQLAlchemy pour le portail client.
Contient les tables liées aux vols, aéroports, avions, réservations et billets.
"""

from app import db
from datetime import datetime

class Reservation(db.Model):
    __tablename__ = 'reservations'
    __table_args__ = {'extend_existing': True}
    id_reservation = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer, db.ForeignKey('clients.id_client'), nullable=False)
    date_reservation = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.Enum('Confirmee', 'Annulee', 'En cours', 'En modification', 'Erreur'), default='Confirmee')

    # --- Relations ---
    client = db.relationship('User', backref=db.backref('reservations', lazy='dynamic'))
    billets = db.relationship('Billet', back_populates='reservation', lazy=True, cascade="all, delete-orphan")

class Passager(db.Model):
    __tablename__ = 'passagers'
    id_passager = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_reservation = db.Column(db.Integer, db.ForeignKey('reservations.id_reservation'), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)

    # --- Relations ---
    reservation = db.relationship('Reservation', backref=db.backref('passagers', lazy=True, cascade="all, delete-orphan"))
    billets = db.relationship('Billet', back_populates='passager', lazy=True)

class Billet(db.Model):
    __tablename__ = 'billets'
    id_billet = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_reservation = db.Column(db.Integer, db.ForeignKey('reservations.id_reservation'), nullable=False)
    id_vol = db.Column(db.Integer, db.ForeignKey('vols.id_vol'), nullable=False)
    classe = db.Column(db.Enum('Eco', 'Business', 'First'), nullable=False, default='Eco')
    options_repas = db.Column(db.SmallInteger, nullable=True, default=0)
    bagages_sup = db.Column(db.Integer, nullable=True, default=0)
    siege = db.Column(db.String(4), nullable=True)
    id_passager = db.Column(db.Integer, db.ForeignKey('passagers.id_passager'), nullable=True)

    # --- Relations ---
    reservation = db.relationship('Reservation', back_populates='billets')
    vol = db.relationship('Vols', back_populates='billets')
    passager = db.relationship('Passager', back_populates='billets')

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
    
    # Numéro de téléphone (format +33X XX XX XX XX)
    numero_telephone = db.Column(db.String(20), nullable=True)
    
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

    def get_prochains_vols(self):
        """Retourne les prochains billets (vols) confirmés pour cet utilisateur"""
        return db.session.query(Billet)\
            .join(Reservation)\
            .join(Vols)\
            .filter(Reservation.id_client == self.id_client)\
            .filter(Reservation.statut == 'Confirmee')\
            .filter(Vols.date_heure_dep_utc >= datetime.utcnow())\
            .order_by(Vols.date_heure_dep_utc.asc())\
            .all()