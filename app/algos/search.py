"""
Moteur de recherche d'itinéraires de vols O'Buffair.
Gère la recherche de correspondances jusqu'à 2 escales.
"""

from app import db
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

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

    # 1. Vols Directs
    direct_flights = db.session.execute(text("""
        SELECT * FROM vols 
        WHERE id_aeroport_depart = :origin 
        AND id_aeroport_arrivee = :destination
        AND date_heure_dep_utc >= :actual_start_bound
        AND date_heure_dep_utc < :end_bound_dt
    """), {
        'origin': origin,
        'destination': destination,
        'actual_start_bound': actual_start_bound,
        'end_bound_dt': end_bound_dt
    }).mappings().all()
    
    for f in direct_flights:
        # Filtrage exact sur le fuseau horaire local de la machine
        f_local = f['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
        if f_local.date() == target_date:
            valid_itineraries.append([f])

    # 2. Vols avec 1 Escale
    if max_stops >= 1:
        first_legs = db.session.execute(text("""
            SELECT * FROM vols 
            WHERE id_aeroport_depart = :origin 
            AND id_aeroport_arrivee != :destination
            AND date_heure_dep_utc >= :actual_start_bound
            AND date_heure_dep_utc < :end_bound_dt
        """), {
            'origin': origin,
            'destination': destination,
            'actual_start_bound': actual_start_bound,
            'end_bound_dt': end_bound_dt
        }).mappings().all()
        
        filtered_first_legs = []
        for leg1 in first_legs:
            leg1_local = leg1['date_heure_dep_utc'].replace(tzinfo=timezone.utc).astimezone()
            if leg1_local.date() == target_date:
                filtered_first_legs.append(leg1)
                
        if filtered_first_legs:
            min_global_dep = min(leg['date_heure_arr_utc'] + timedelta(minutes=40) for leg in filtered_first_legs)
            max_global_dep = max(leg['date_heure_arr_utc'] + timedelta(hours=12) for leg in filtered_first_legs)
            
            arrival_airports = list(set(leg['id_aeroport_arrivee'] for leg in filtered_first_legs))
            in_clause = ', '.join(f"'{iata}'" for iata in arrival_airports)
            
            second_legs_all = db.session.execute(text(f"""
                SELECT * FROM vols 
                WHERE id_aeroport_depart IN ({in_clause})
                AND date_heure_dep_utc >= :min_dep
                AND date_heure_dep_utc <= :max_dep
            """), {
                'min_dep': min_global_dep,
                'max_dep': max_global_dep
            }).mappings().all()
            
            potential_two_stops = []

            for leg1 in filtered_first_legs:
                min_dep = leg1['date_heure_arr_utc'] + timedelta(minutes=40) # Escale min
                max_dep = leg1['date_heure_arr_utc'] + timedelta(hours=12)   # Escale max
                
                for leg2 in second_legs_all:
                    if leg2['id_aeroport_depart'] == leg1['id_aeroport_arrivee'] and min_dep <= leg2['date_heure_dep_utc'] <= max_dep:
                        # Prévention des boucles de correspondance (ex: A -> B -> A)
                        if leg2['id_aeroport_arrivee'] == origin:
                            continue
                            
                        if leg2['id_aeroport_arrivee'] == destination:
                            # C'est bien la destination finale : 1 escale
                            valid_itineraries.append([leg1, leg2])
                            
                        elif max_stops >= 2:
                            # On met de côté cette correspondance pour chercher un troisième segment
                            potential_two_stops.append((leg1, leg2))
                            
            # 3. Vols avec 2 Escales
            if max_stops >= 2 and potential_two_stops:
                min_global_dep_3 = min(leg2['date_heure_arr_utc'] + timedelta(minutes=40) for _, leg2 in potential_two_stops)
                max_global_dep_3 = max(leg2['date_heure_arr_utc'] + timedelta(hours=12) for _, leg2 in potential_two_stops)
                
                arrival_airports_2 = list(set(leg2['id_aeroport_arrivee'] for _, leg2 in potential_two_stops))
                in_clause_2 = ', '.join(f"'{iata}'" for iata in arrival_airports_2)
                
                third_legs_all = db.session.execute(text(f"""
                    SELECT * FROM vols 
                    WHERE id_aeroport_depart IN ({in_clause_2})
                    AND id_aeroport_arrivee = :destination
                    AND date_heure_dep_utc >= :min_dep
                    AND date_heure_dep_utc <= :max_dep
                """), {
                    'destination': destination,
                    'min_dep': min_global_dep_3,
                    'max_dep': max_global_dep_3
                }).mappings().all()
                
                for leg1, leg2 in potential_two_stops:
                    min_dep_3 = leg2['date_heure_arr_utc'] + timedelta(minutes=40)
                    max_dep_3 = leg2['date_heure_arr_utc'] + timedelta(hours=12)
                    
                    for leg3 in third_legs_all:
                        if leg3['id_aeroport_depart'] == leg2['id_aeroport_arrivee'] and min_dep_3 <= leg3['date_heure_dep_utc'] <= max_dep_3:
                            valid_itineraries.append([leg1, leg2, leg3])

    return valid_itineraries