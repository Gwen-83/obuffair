"""
Moteur de recherche d'itinéraires de vols O'Buffair.
Gère la recherche de correspondances jusqu'à 2 escales.
"""

from app import db
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

_airport_offsets_cache = {}
def get_local_time(dt_utc, iata_code):
    """Récupère dynamiquement l'heure locale d'un aéroport sans dépendre de l'OS du serveur."""
    if not _airport_offsets_cache:
        try:
            rows = db.session.execute(text("SELECT id_aeroport, decalage_utc FROM aeroports")).fetchall()
            for r in rows: _airport_offsets_cache[r[0]] = r[1]
        except Exception: pass
    offset = _airport_offsets_cache.get(iata_code, "+00:00")
    try:
        sign = 1 if offset[0] == '+' else -1
        h, m = int(offset[1:3]), int(offset[4:6]) if len(offset) > 4 else 0
        return dt_utc + timedelta(hours=sign*h, minutes=sign*m)
    except Exception: return dt_utc

def search_itineraries(origin, destination, target_date_str, max_stops=2):
    """Algorithme de recherche avec filtrage par date locale de la machine"""
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return []

    valid_itineraries = []
    
    # Requête large en BDD : +/- 1 jour pour compenser les décalages horaires UTC vs Local
    start_bound = target_date - timedelta(days=1)
    end_bound = target_date + timedelta(days=2)
    
    # Conversion en datetime strict pour éviter l'usage de DATE() en SQL (qui détruit les index)
    start_bound_dt = datetime(start_bound.year, start_bound.month, start_bound.day)
    end_bound_dt = datetime(end_bound.year, end_bound.month, end_bound.day)
    
    # Sécurité anti-fantômes : on ne remonte aucun vol qui part dans moins de 2 heures
    now_bound = datetime.utcnow() + timedelta(hours=2)
    
    # OPTIMISATION : Fusion des bornes pour alléger l'évaluation conditionnelle SQL
    actual_start_bound = max(start_bound_dt, now_bound)

    def build_itineraries(vol_ids_list):
        if not vol_ids_list: return
        
        flat_ids = tuple(set(vid for tpl in vol_ids_list for vid in tpl))
        all_vols = db.session.execute(text(
            "SELECT * FROM vols WHERE id_vol IN :ids"
        ), {'ids': flat_ids}).mappings().all()
        
        vols_dict = {v['id_vol']: v for v in all_vols}
        
        for tpl in vol_ids_list:
            leg_list = [vols_dict[vid] for vid in tpl if vid in vols_dict]
            if len(leg_list) == len(tpl):
                f_local = get_local_time(leg_list[0]['date_heure_dep_utc'], leg_list[0]['id_aeroport_depart'])
                if f_local.date() == target_date:
                    valid_itineraries.append(leg_list)

    # 1. Vols Directs
    direct_ids = db.session.execute(text("""
        SELECT id_vol FROM vols 
        WHERE id_aeroport_depart = :origin 
        AND id_aeroport_arrivee = :destination
        AND date_heure_dep_utc >= :actual_start_bound
        AND date_heure_dep_utc < :end_bound_dt
    """), {'origin': origin, 'destination': destination, 'actual_start_bound': actual_start_bound, 'end_bound_dt': end_bound_dt}).fetchall()
    build_itineraries([ (row[0],) for row in direct_ids ])

    # 2. Vols avec 1 Escale
    if max_stops >= 1:
        one_stop_ids = db.session.execute(text("""
            SELECT v1.id_vol, v2.id_vol
            FROM vols v1
            JOIN vols v2 ON v1.id_aeroport_arrivee = v2.id_aeroport_depart
            WHERE v1.id_aeroport_depart = :origin AND v2.id_aeroport_arrivee = :destination
            AND v1.date_heure_dep_utc >= :start AND v1.date_heure_dep_utc < :end
            AND v2.date_heure_dep_utc >= DATE_ADD(v1.date_heure_arr_utc, INTERVAL 40 MINUTE)
            AND v2.date_heure_dep_utc <= DATE_ADD(v1.date_heure_arr_utc, INTERVAL 12 HOUR)
            AND v2.id_aeroport_arrivee != v1.id_aeroport_depart
        """), {'origin': origin, 'destination': destination, 'start': actual_start_bound, 'end': end_bound_dt}).fetchall()
        build_itineraries(one_stop_ids)

    # 3. Vols avec 2 Escales
    if max_stops >= 2:
        two_stop_ids = db.session.execute(text("""
            SELECT v1.id_vol, v2.id_vol, v3.id_vol
            FROM vols v1
            JOIN vols v2 ON v1.id_aeroport_arrivee = v2.id_aeroport_depart
            JOIN vols v3 ON v2.id_aeroport_arrivee = v3.id_aeroport_depart
            WHERE v1.id_aeroport_depart = :origin AND v3.id_aeroport_arrivee = :destination
            AND v1.date_heure_dep_utc >= :start AND v1.date_heure_dep_utc < :end
            AND v2.date_heure_dep_utc >= DATE_ADD(v1.date_heure_arr_utc, INTERVAL 40 MINUTE)
            AND v2.date_heure_dep_utc <= DATE_ADD(v1.date_heure_arr_utc, INTERVAL 12 HOUR)
            AND v3.date_heure_dep_utc >= DATE_ADD(v2.date_heure_arr_utc, INTERVAL 40 MINUTE)
            AND v3.date_heure_dep_utc <= DATE_ADD(v2.date_heure_arr_utc, INTERVAL 12 HOUR)
            AND v2.id_aeroport_arrivee != v1.id_aeroport_depart
            AND v3.id_aeroport_arrivee != v2.id_aeroport_depart
            AND v3.id_aeroport_arrivee != v1.id_aeroport_depart
        """), {'origin': origin, 'destination': destination, 'start': actual_start_bound, 'end': end_bound_dt}).fetchall()
        build_itineraries(two_stop_ids)

    return valid_itineraries