import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Variable globale pour mémoriser la dernière fois que l'algorithme a été exécuté
_last_update_time = None

def update_flight_statuses_if_needed():
    """
    Vérifie si 10 minutes se sont écoulées depuis la dernière exécution.
    Si oui, met à jour le statut des vols selon les règles.
    """
    global _last_update_time
    now = datetime.utcnow()
    
    # On vérifie si 10 minutes se sont écoulées
    if _last_update_time is not None and now < _last_update_time + timedelta(minutes=10):
        return
        
    _last_update_time = now
    
    # Import ici pour éviter les imports circulaires
    from app import db
    from app.model import Vols
    
    try:
        # On récupère tous les vols non terminés ou annulés
        vols = Vols.query.filter(Vols.statut.notin_(['terminé', 'annulé'])).all()
        
        updates = 0
        for vol in vols:
            nouveau_statut = vol.statut
            dep = vol.date_heure_dep_utc
            arr = vol.date_heure_arr_utc
            
            if arr is None or dep is None:
                continue
                
            # 1. Plus de 30 min après l'arrivée -> terminé
            if now >= arr + timedelta(minutes=30):
                nouveau_statut = 'terminé'
            # 2. 15 min après l'arrivée (jusqu'à 30 min) -> débarquement
            elif arr + timedelta(minutes=15) <= now < arr + timedelta(minutes=30):
                nouveau_statut = 'débarquement'
            # 3. Pendant la durée du vol -> en vol
            # On inclut jusqu'à 15 minutes après l'arrivée pour faire la jonction
            elif dep <= now < arr + timedelta(minutes=15):
                nouveau_statut = 'en vol'
            # 4. 15 min avant l'heure programmée -> embarquement
            elif dep - timedelta(minutes=15) <= now < dep:
                nouveau_statut = 'embarquement'
            
            # Mise à jour si le statut a changé
            if nouveau_statut != vol.statut:
                vol.statut = nouveau_statut
                updates += 1
        
        if updates > 0:
            db.session.commit()
            logger.info(f"[Algorithme Statut Vols] {updates} vols mis à jour.")

    except Exception as e:
        # En cas d'erreur, on annule les éventuelles modifications partielles
        db.session.rollback()
        logger.error(f"[Algorithme Statut Vols] Erreur lors de la mise à jour : {e}")

def init_status_hook(app):
    """
    Enregistre la fonction de mise à jour pour s'exécuter avant chaque requête Flask.
    """
    @app.before_request
    def check_flight_status_on_request():
        update_flight_statuses_if_needed()
