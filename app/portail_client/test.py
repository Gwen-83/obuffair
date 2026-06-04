"""
Formulaires client : recherche vols, édition profil, modification réservation.
Validation des paramètres de recherche (dates, passagers, aéroports).
"""

from app import db

def get_test_output():
    """Exécute une requête de test et renvoie les données brutes."""
    try:
        result = db.session.execute(db.text("SELECT id_aeroport FROM aeroports ORDER BY ville DESC")).fetchall()
        return str(result)
    except Exception as e:
        return f"Erreur : {e}"
