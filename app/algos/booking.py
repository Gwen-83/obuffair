"""
Algorithmes et logique métier liés à la réservation de vols.
Gestion des créations, modifications de PNR et calculs de fidélité.
"""

import random
import string
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.orm import joinedload
from app import db
from app.model import Reservation, Passager, Billet, User

TARIFS_OPTIONS = {
    'bagages_eco': {
        '0': 0,
        '1': 45,
        '2': 80,
        '3': 115
    },
    'repas_eco': {
        'standard': 0,
        'premium': 15,
        'vegetarien': 15
    }
}

def sync_loyalty_points(user):
    """Calcule et met à jour automatiquement les points de fidélité d'un utilisateur en analysant ses vols confirmés."""
    if not user: return
    repas_map_rev = {0: 'standard', 1: 'premium', 2: 'vegetarien', 3: 'gastronomique'}
    total_euros = 0
    
    try:
        reservations = user.reservations.filter_by(statut='Confirmee').options(
            joinedload(Reservation.billets).joinedload(Billet.vol)
        ).all()
        
        for resa in reservations:
            for billet in resa.billets:
                vol = billet.vol
                if not vol: continue
                
                # Calcul du prix du billet selon sa classe
                base_price = float(vol.prix_de_base)
                if billet.classe == 'First':
                    prix_billet = base_price * 4.0
                elif billet.classe == 'Business':
                    prix_billet = base_price * 2.5
                else:
                    prix_billet = max(50.0, base_price)
                
                # Ajout des options
                rep_str = repas_map_rev.get(billet.options_repas, 'standard')
                bag_val = str(billet.bagages_sup)
                
                if billet.classe == 'Eco':
                    prix_billet += TARIFS_OPTIONS['bagages_eco'].get(bag_val, 0)
                    prix_billet += TARIFS_OPTIONS['repas_eco'].get(rep_str, 0)
                else:
                    prix_billet += TARIFS_OPTIONS['bagages_eco'].get(bag_val, 0)
                    
                total_euros += prix_billet

        pts = int(total_euros)
        if user.points_fidelite_accumules != pts or user.points_fidelite != pts:
            user.points_fidelite = pts
            user.points_fidelite_accumules = pts
            db.session.commit()
    except Exception as e:
        print(f"Erreur sync_loyalty_points: {e}")

def create_reservation_in_db(session_data):
    """
    Logique Métier : Crée une réservation complète (Reservation, Passagers, Billets) 
    à partir des données en session et l'insère en BDD en évitant les surréservations (race conditions).
    Retourne l'ID de la réservation en cas de succès, None sinon.
    """
    try:
        client_id = session_data.get('user_id')
        passengers_info = session_data.get('passagers_data', {})
        options_info = session_data.get('options', {}).get('passagers', [])
        vol_aller = session_data.get('vol_aller', {})
        vol_retour = session_data.get('vol_retour', {})
        search_params = session_data.get('search_params', {})
        nb_passagers = int(search_params.get('passagers', 1))

        if not client_id or not vol_aller:
            raise ValueError("Identifiant client ou vol aller manquant dans la session.")

        # 1. Créer la réservation principale
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        new_reservation = Reservation(
            id_client=client_id,
            date_reservation=datetime.utcnow(),
            statut='Confirmee',
            pnr=pnr
        )
        db.session.add(new_reservation)
        db.session.flush()  # Pour obtenir new_reservation.id_reservation

        # Récupérer l'utilisateur principal (Master)
        master_user = db.session.get(User, client_id)

        # 2. Créer les passagers et les billets associés
        for i in range(nb_passagers):
            p_num = i + 1
            
            # Remplissage par défaut avec le Master si c're le Passager 1 et que les infos sont vides
            p_nom = passengers_info.get(f'nom_{p_num}', '').strip() or (master_user.nom if p_num == 1 and master_user else 'N/A')
            p_prenom = passengers_info.get(f'prenom_{p_num}', '').strip() or (master_user.prenom if p_num == 1 and master_user else 'N/A')

            # Créer le passager
            new_passager = Passager(
                id_reservation=new_reservation.id_reservation,
                nom=p_nom,
                prenom=p_prenom
            )
            db.session.add(new_passager)
            db.session.flush() # Pour obtenir new_passager.id_passager

            # Sécurisation en cas de données d'options incomplètes
            p_options = options_info[i] if i < len(options_info) else {}
            
            # Convertir les options en format BDD
            repas_map = {'standard': 0, 'premium': 1, 'vegetarien': 2, 'gastronomique': 3}
            repas_val = repas_map.get(str(p_options.get('repas', 'standard')).lower(), 0)
            
            try:
                # Extrait le chiffre de '2_23kg' ou '1' de manière robuste
                bagages_str = str(p_options.get('bagages', '0')).split('_')[0]
                bagages_val = int(bagages_str)
            except (ValueError, TypeError):
                bagages_val = 0

            # Créer les billets pour chaque segment de vol
            def create_billets_for_legs(vol_data, classe_key, sieges_key):
                if not vol_data or not vol_data.get('id_vol'): return
                leg_ids = str(vol_data.get('id_vol', '')).split('_')
                sieges = p_options.get(sieges_key, [])
                
                classe = p_options.get(classe_key, 'Eco')
                # Protection contre une valeur "Mixte" (hors contrainte ENUM)
                if classe not in ['Eco', 'Business', 'First']:
                    classe = 'Eco'
                
                for idx, leg_id in enumerate(leg_ids):
                    if not leg_id: continue
                    siege = sieges[idx] if idx < len(sieges) else None
                    if siege == "": siege = None
                    
                    # Anti-Race Condition : Vérification stricte que le siège n'a pas été pris
                    if siege:
                        seat_taken = db.session.execute(text("""
                            SELECT 1 FROM billets b 
                            JOIN reservations r ON b.id_reservation = r.id_reservation 
                            WHERE b.id_vol = :id_vol AND b.siege = :siege AND r.statut != 'Annulee'
                        """), {'id_vol': int(leg_id), 'siege': siege}).fetchone()
                        
                        if seat_taken:
                            raise ValueError(f"Le siège {siege} sur le vol {leg_id} vient d'être réservé par un autre client.")

                    billet = Billet(
                        id_reservation=new_reservation.id_reservation,
                        id_vol=int(leg_id),
                        id_passager=new_passager.id_passager,
                        classe=classe,
                        options_repas=repas_val,
                        bagages_sup=bagages_val,
                        siege=siege
                    )
                    db.session.add(billet)

            create_billets_for_legs(vol_aller, 'classe_aller', 'sieges_aller')
            create_billets_for_legs(vol_retour, 'classe_retour', 'sieges_retour')

        db.session.commit()
        if master_user:
            sync_loyalty_points(master_user)
        return new_reservation.id_reservation, None

    except Exception as e:
        db.session.rollback()
        print(f"ERREUR CRÉATION RÉSERVATION: {e}")
        return None, str(e)

def update_reservation_in_db(session_data, pnr):
    """
    Logique Métier : Met à jour une réservation existante suite à une modification par le client.
    Supprime les anciens billets et les recrée avec les nouvelles options ou les nouveaux vols.
    """
    try:
        client_id = session_data.get('user_id')
        reservation = db.session.query(Reservation).filter_by(pnr=pnr, id_client=client_id).first()
        if not reservation:
            raise ValueError("Réservation introuvable.")
            
        # Suppression propre des anciens billets et passagers
        for b in reservation.billets:
            db.session.delete(b)
        db.session.flush()
        for p in reservation.passagers:
            db.session.delete(p)
        db.session.flush()

        # Nous déléguons la reconstruction exacte au même helper que la création
        # En re-assignant le PNR et la date d'origine pour éviter d'altérer l'historique
        original_date = reservation.date_reservation
        db.session.delete(reservation)
        db.session.flush()
        
        new_res_id, error = create_reservation_in_db(session_data)
        if error:
            raise ValueError(error)
            
        # Restauration des attributs d'origine
        new_resa = db.session.get(Reservation, new_res_id)
        new_resa.pnr = pnr
        new_resa.date_reservation = original_date
        db.session.commit()
        
        return new_res_id, None
    except Exception as e:
        db.session.rollback()
        return None, str(e)

def group_flights_by_journey(billets):
    """
    Utilitaire analytique : Regroupe les billets d'une réservation en trajets distincts (Aller et Retour).
    Se base sur la continuité des vols et les intervalles temporels pour séparer un AR d'un AS avec escales.
    """
    if not billets: return [], []
    vols_list = sorted(list({b.id_vol: b.vol for b in billets}.values()), key=lambda v: v.date_heure_dep_utc)
    if not vols_list: return [], []
    
    is_ar = len(vols_list) > 1 and vols_list[-1].id_aeroport_arrivee == vols_list[0].id_aeroport_depart
    if is_ar:
        gaps = [(i+1, vols_list[i+1].date_heure_dep_utc - vols_list[i].date_heure_arr_utc) for i in range(len(vols_list) - 1)]
        if gaps:
            split_idx, max_gap = max(gaps, key=lambda item: item[1])
            if max_gap > timedelta(hours=12):
                return vols_list[:split_idx], vols_list[split_idx:]
    return vols_list, []