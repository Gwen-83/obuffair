import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Variable globale pour mémoriser la dernière fois que l'algorithme a été exécuté
_last_update_time = None

def update_flight_statuses_if_needed():
    """
    Vérifie si 1 minute s'est écoulée depuis la dernière exécution.
    Si oui, met à jour le statut des vols selon les règles.
    """
    global _last_update_time
    now = datetime.utcnow()
    
    # On vérifie si 1 minute s'est écoulée (au lieu de 10) pour plus de réactivité sur les départs
    if _last_update_time is not None and now < _last_update_time + timedelta(minutes=1):
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
            
            if arr is None or dep is None or arr <= dep:
                continue
                
            # Si le vol est marqué manuellement "retardé", on le laisse tel quel 
            # jusqu'à ce que l'heure d'arrivée prévue soit dépassée.
            if vol.statut == 'retardé' and now < arr:
                continue
                
            # 1. Plus de 30 min après l'arrivée -> terminé
            if now >= arr + timedelta(minutes=30):
                nouveau_statut = 'terminé'
            # 2. Dès l'arrivée jusqu'à 30 min après -> débarquement
            elif arr <= now < arr + timedelta(minutes=30):
                nouveau_statut = 'débarquement'
            # 3. Pendant le vol (de l'heure de départ à l'heure d'arrivée) -> en vol
            elif dep <= now < arr:
                nouveau_statut = 'en vol'
            # 4. De 45 min avant l'heure programmée jusqu'au départ -> embarquement
            elif dep - timedelta(minutes=45) <= now < dep:
                nouveau_statut = 'embarquement'
            # 5. Plus de 45 min avant le départ -> à l'heure
            elif now < dep - timedelta(minutes=45):
                nouveau_statut = "à l'heure"
            
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
