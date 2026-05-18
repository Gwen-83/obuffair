"""
Application Flask avec connexion MySQL.
Tout en un seul fichier pour la simplicité.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# Initialiser SQLAlchemy (vide d'abord, sera lié à l'app après)
db = SQLAlchemy()


def create_app():
    """Créer et configurer l'application Flask"""
    
    app = Flask(__name__)
    
    # ========== CONFIGURATION ==========
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'
    
    # Base de données MySQL distante
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://gwenael.drouet:password@enac.darties.fr/gwenael.drouet_Projet_obuffair'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = True
    
    # ========== INITIALISER LA DB ==========
    db.init_app(app)
    
    # ========== ROUTES DE TEST ==========
    @app.route('/')
    def index():
        return {'message': 'Bienvenue sur Obuffair!', 'status': 'OK'}
    
    @app.route('/test-db')
    def test_db():
        """Tester la connexion à la base"""
        try:
            db.session.execute(text('SELECT 1'))
            return {
                'status': 'Connexion réussie!',
                'database': 'MySQL distant sur enac.darties.fr'
            }
        except Exception as e:
            return {'status': 'Erreur', 'error': str(e)}, 500
    
    @app.route('/data')
    def get_all_data():
        """Afficher TOUTES les données de la base"""
        try:
            data = {}
            
            # ========== TABLE UTILISATEUR ==========
            result = db.session.execute(text('SELECT * FROM clients'))
            users = [dict(row._mapping) for row in result]
            data['utilisateur'] = users
            print(f"✅ Utilisateurs ({len(users)}): {users}")
            
            # ========== TABLE VOL ==========
            result = db.session.execute(text('SELECT * FROM vols'))
            flights = [dict(row._mapping) for row in result]
            data['vol'] = flights
            print(f"✅ Vols ({len(flights)}): {flights}")
            
            # ========== TABLE AVION ==========
            result = db.session.execute(text('SELECT * FROM avions'))
            aircrafts = [dict(row._mapping) for row in result]
            data['avion'] = aircrafts
            print(f"✅ Avions ({len(aircrafts)}): {aircrafts}")
            
            # ========== TABLE AEROPORT ==========
            result = db.session.execute(text('SELECT * FROM aeroports'))
            airports = [dict(row._mapping) for row in result]
            data['aeroport'] = airports
            print(f"✅ Aéroports ({len(airports)}): {airports}")
            
            # ========== TABLE RESERVATION ==========
            result = db.session.execute(text('SELECT * FROM reservations'))
            bookings = [dict(row._mapping) for row in result]
            data['reservation'] = bookings
            print(f"✅ Réservations ({len(bookings)}): {bookings}")
            
            # ========== TABLE BILLET_SEGMENT ==========
            result = db.session.execute(text('SELECT * FROM billets'))
            tickets = [dict(row._mapping) for row in result]
            data['billet_segment'] = tickets
            print(f"✅ Billets ({len(tickets)}): {tickets}")
            
            return {
                'status': 'Succès',
                'message': f'Données récupérées de {len(data)} tables',
                'data': data
            }
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erreur: {error_msg}")
            return {'status': 'Erreur', 'error': error_msg}, 500
    
    return app
