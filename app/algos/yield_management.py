"""
OBufFair — Algorithme de tarification dynamique
================================================
Modèle multiplicatif :  prix_final = prix_de_base × Π(multiplicateurs)

Chaque facteur est un coefficient indépendant compris généralement entre 0.7 et 1.6.
Le produit est ensuite plafonné entre PRIX_MINIMUM_RATIO et PRIX_MAXIMUM_RATIO
pour éviter des prix aberrants.

Facteurs pris en compte (par ordre d'importance) :
  1. Remplissage + pression temporelle  (le plus impactant)
  2. Fenêtre d'anticipation
  3. Saison / vacances scolaires / jours fériés
  4. Jour de la semaine
  5. Heure de départ
  6. Météo à destination
  7. Événements à destination
  8. Classe de voyage
  9. Concurrence (optionnel)
"""

import math
from datetime import datetime
from enum import Enum

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE CALIBRATION
# ─────────────────────────────────────────────────────────────────────────────

PRIX_MINIMUM_RATIO = 0.40   # jamais en dessous de 40 % du prix de base
PRIX_MAXIMUM_RATIO = 3.50   # jamais au dessus de 350 % du prix de base


# ═════════════════════════════════════════════════════════════════════════════
# 1. REMPLISSAGE + PRESSION TEMPORELLE  (facteur le plus critique)
# ═════════════════════════════════════════════════════════════════════════════

def multiplicateur_remplissage(taux: float, jours_avant: int) -> float:
    """
    Combine le taux de remplissage réel avec la vitesse de remplissage attendue.

    Un vol à 70 % plein à J-60 = situation excellente → prix en hausse.
    Un vol à 70 % plein à J-1  = situation normale   → pas de hausse particulière.
    Un vol à 30 % plein à J-2  = destockage urgent   → solde agressif.

    Paramètres
    ----------
    taux       : float  — taux de remplissage actuel, 0.0 → 1.0
    jours_avant: int    — jours restants avant le départ
    """

    # --- Courbe de remplissage "normal" selon le délai ---
    # Calibrée sur des données historiques type court/moyen-courrier européen.
    def remplissage_attendu(j: int) -> float:
        if j >= 180: return 0.10
        if j >= 90:  return 0.20
        if j >= 60:  return 0.30
        if j >= 30:  return 0.50
        if j >= 14:  return 0.65
        if j >= 7:   return 0.75
        if j >= 3:   return 0.82
        if j >= 1:   return 0.88
        return 0.92  # jour J

    attendu = remplissage_attendu(jours_avant)

    # Ratio pression : > 1 = se remplit plus vite que prévu, < 1 = plus lent
    ratio_pression = taux / max(attendu, 0.01)

    # --- Multiplicateur de base selon le taux réel ---
    if taux < 0.20:   m_base = 0.80
    elif taux < 0.40: m_base = 0.90
    elif taux < 0.60: m_base = 1.00
    elif taux < 0.75: m_base = 1.12
    elif taux < 0.85: m_base = 1.28
    elif taux < 0.93: m_base = 1.50
    else:             m_base = 1.75  # quasi complet

    # --- Ajustement selon la pression temporelle ---
    # Amplification douce : ratio 1.5 (50 % plus rapide) → +15 % supplémentaires
    ajustement = 1.0 + (ratio_pression - 1.0) * 0.30
    ajustement = max(0.75, min(1.50, ajustement))

    # --- Cas spéciaux ---

    # Déstockage last-minute : vol peu rempli à J-2 ou moins
    if jours_avant <= 2 and taux < 0.40:
        return 0.65   # solde agressif, on préfère remplir

    # Urgence last-minute : vol presque plein à J-3 ou moins
    if jours_avant <= 3 and taux >= 0.88:
        return m_base * ajustement * 1.20  # bonus +20 %

    return m_base * ajustement


# ═════════════════════════════════════════════════════════════════════════════
# 2. FENÊTRE D'ANTICIPATION (early bird vs last minute)
# ═════════════════════════════════════════════════════════════════════════════

def multiplicateur_anticipation(jours_avant: int) -> float:
    """
    Récompense les réservations très à l'avance (early bird),
    et pénalise modérément le last-minute modéré.

    Note : distinct du remplissage — s'applique toujours, même si le vol est vide.
    """
    if jours_avant >= 180: return 0.78   # tarif early bird maximum
    if jours_avant >= 120: return 0.84
    if jours_avant >= 90:  return 0.90
    if jours_avant >= 60:  return 0.95
    if jours_avant >= 30:  return 1.00   # référence neutre
    if jours_avant >= 14:  return 1.08
    if jours_avant >= 7:   return 1.18
    if jours_avant >= 3:   return 1.30
    if jours_avant >= 1:   return 1.45
    return 1.60                           # réservation le jour même


# ═════════════════════════════════════════════════════════════════════════════
# 3. SAISON / VACANCES SCOLAIRES / JOURS FÉRIÉS
# ═════════════════════════════════════════════════════════════════════════════

# Vacances scolaires françaises 2025-2026 (dates moyennées zones A/B/C)
_VACANCES = [
    (datetime(2025, 10, 18), datetime(2025, 11,  3), "Toussaint"),
    (datetime(2025, 12, 20), datetime(2026,  1,  5), "Noël"),
    (datetime(2026,  2, 14), datetime(2026,  3,  2), "Hiver"),
    (datetime(2026,  4, 11), datetime(2026,  4, 27), "Printemps"),
    (datetime(2026,  7,  4), datetime(2026,  9,  1), "Été"),
]

_JOURS_FERIES = [
    datetime(2026,  1,  1),   # Jour de l'An
    datetime(2026,  5,  1),   # Fête du Travail
    datetime(2026,  5,  8),   # Victoire 1945
    datetime(2026,  5, 25),   # Ascension
    datetime(2026,  6,  5),   # Pentecôte
    datetime(2026,  7, 14),   # Fête Nationale
    datetime(2026,  8, 15),   # Assomption
    datetime(2026, 11,  1),   # Toussaint
    datetime(2026, 11, 11),   # Armistice
    datetime(2026, 12, 25),   # Noël
]

def multiplicateur_saison(date_depart: datetime) -> float:
    """
    Applique un coefficient selon la période calendaire.
    Vacances Noël et été = pic maximal.
    Janvier/Février hors vacances = basse saison.
    """
    mois = date_depart.month

    # Vacances scolaires
    for debut, fin, nom in _VACANCES:
        if debut <= date_depart <= fin:
            if nom in ("Noël", "Été"):
                return 1.45   # pic absolu
            return 1.25       # autres vacances

    # Veille, jour J ou lendemain d'un jour férié
    for ferie in _JOURS_FERIES:
        delta = abs((date_depart.date() - ferie.date()).days)
        if delta <= 1:
            return 1.30

    # Saison estivale hors vacances officielles (juin, début juillet, fin août)
    if mois == 6:
        return 1.18

    # Basse saison structurelle
    if mois in (1, 2, 11):
        return 0.85

    # Printemps / automne doux
    if mois in (3, 4, 5, 9, 10):
        return 1.00

    return 1.00   # décembre hors fêtes


# ═════════════════════════════════════════════════════════════════════════════
# 4. JOUR DE LA SEMAINE
# ═════════════════════════════════════════════════════════════════════════════

def multiplicateur_jour_semaine(date_depart: datetime) -> float:
    """
    Vendredi (départs week-end) et dimanche (retours) sont les plus chers.
    Mardi et mercredi sont structurellement creux.
    Un bonus est ajouté au vendredi soir (départ week-end premium).
    """
    jour  = date_depart.weekday()   # 0 = lundi, 6 = dimanche
    heure = date_depart.hour

    grille = {
        0: 1.05,   # Lundi
        1: 0.88,   # Mardi      ← creux
        2: 0.88,   # Mercredi   ← creux
        3: 1.00,   # Jeudi
        4: 1.22,   # Vendredi   ← départs week-end
        5: 1.10,   # Samedi
        6: 1.28,   # Dimanche   ← retours
    }
    m = grille[jour]

    # Vendredi soir (17h–21h) = départ week-end très demandé
    if jour == 4 and 17 <= heure <= 21:
        m *= 1.08

    # Dimanche soir (17h–21h) = retours tardifs, encore plus chers
    if jour == 6 and 17 <= heure <= 21:
        m *= 1.06

    return m


# ═════════════════════════════════════════════════════════════════════════════
# 5. HEURE DE DÉPART
# ═════════════════════════════════════════════════════════════════════════════

def multiplicateur_heure(date_depart: datetime) -> float:
    """
    Les créneaux business (7h-9h, 17h-19h) sont plus chers.
    La nuit profonde et le très tôt matin sont moins chers.
    """
    h = date_depart.hour

    if  0 <= h <  5: return 0.78   # nuit profonde (vols low-cost)
    if  5 <= h <  7: return 0.88   # très tôt matin
    if  7 <= h < 10: return 1.15   # heure de pointe matin (business)
    if 10 <= h < 12: return 1.05   # milieu de matinée
    if 12 <= h < 14: return 1.00   # déjeuner
    if 14 <= h < 17: return 0.95   # après-midi creux
    if 17 <= h < 20: return 1.15   # heure de pointe soir (business)
    if 20 <= h < 22: return 1.00   # début de soirée
    return 0.85                     # fin de soirée / nuit


# ═════════════════════════════════════════════════════════════════════════════
# 6. MÉTÉO À DESTINATION
# ═════════════════════════════════════════════════════════════════════════════

class ConditionMeteo(Enum):
    EXCELLENT    = "excellent"      # grand soleil, chaleur idéale
    BON          = "bon"            # beau temps sans excès
    NEUTRE       = "neutre"         # couvert / temps de saison
    MAUVAIS      = "mauvais"        # pluie, vent fort
    TRES_MAUVAIS = "tres_mauvais"   # tempête, alerte météo, neige

def multiplicateur_meteo(
    condition: ConditionMeteo,
    est_destination_soleil: bool = False
) -> float:
    """
    Impact météo amplifié pour les destinations balnéaires/ski
    où le temps est le principal motif de voyage.

    est_destination_soleil : True pour destinations mer, montagne (été/hiver),
                             plages tropicales, etc.
    """
    if est_destination_soleil:
        grille = {
            ConditionMeteo.EXCELLENT:    1.18,
            ConditionMeteo.BON:          1.08,
            ConditionMeteo.NEUTRE:       1.00,
            ConditionMeteo.MAUVAIS:      0.88,
            ConditionMeteo.TRES_MAUVAIS: 0.75,
        }
    else:
        grille = {
            ConditionMeteo.EXCELLENT:    1.05,
            ConditionMeteo.BON:          1.02,
            ConditionMeteo.NEUTRE:       1.00,
            ConditionMeteo.MAUVAIS:      0.96,
            ConditionMeteo.TRES_MAUVAIS: 0.91,
        }
    return grille[condition]


# ═════════════════════════════════════════════════════════════════════════════
# 7. ÉVÉNEMENTS À DESTINATION
# ═════════════════════════════════════════════════════════════════════════════

class TypeEvenement(Enum):
    AUCUN           = "aucun"
    EVENEMENT_LOCAL = "local"      # festival régional, match de ligue 2
    GRAND_EVENEMENT = "grand"      # concert international, finale de championnat
    MEGA_EVENEMENT  = "mega"       # JO, Coupe du Monde, Grand Prix F1, COP

def multiplicateur_evenement(type_evenement: TypeEvenement) -> float:
    """
    Les grands événements créent une demande inélastique.
    Les gens viennent quoi qu'il en coûte.
    """
    return {
        TypeEvenement.AUCUN:           1.00,
        TypeEvenement.EVENEMENT_LOCAL: 1.12,
        TypeEvenement.GRAND_EVENEMENT: 1.35,
        TypeEvenement.MEGA_EVENEMENT:  1.65,
    }[type_evenement]


# ═════════════════════════════════════════════════════════════════════════════
# 8. CLASSE DE VOYAGE
# ═════════════════════════════════════════════════════════════════════════════

def multiplicateur_classe(classe: str, taux_remplissage_classe: float) -> float:
    """
    Chaque classe a sa propre élasticité prix.
    La Business et First sont moins sensibles aux variations de prix
    (leur clientèle est souvent remboursée par l'employeur).

    classe                  : 'eco', 'business', 'first'
    taux_remplissage_classe : remplissage spécifique à cette classe (0.0 → 1.0)
    """
    # Coefficient d'élasticité : 1.0 = pleinement sensible, 0.0 = insensible
    elasticite = {
        'eco':      1.00,
        'business': 0.55,
        'first':    0.25,
    }.get(classe, 1.00)

    if taux_remplissage_classe >= 0.92:
        delta = +0.28
    elif taux_remplissage_classe >= 0.80:
        delta = +0.15
    elif taux_remplissage_classe >= 0.60:
        delta = +0.05
    elif taux_remplissage_classe <= 0.25:
        delta = -0.12
    elif taux_remplissage_classe <= 0.40:
        delta = -0.06
    else:
        delta = 0.00

    return 1.0 + (delta * elasticite)


# ═════════════════════════════════════════════════════════════════════════════
# 9. CONCURRENCE (optionnel — nécessite une source de données externe)
# ═════════════════════════════════════════════════════════════════════════════

def multiplicateur_concurrence(
    prix_concurrent_moyen: float,
    prix_de_base: float
) -> float:
    """
    Ajustement léger selon le positionnement concurrentiel.
    On ne s'aligne jamais complètement : stratégie de marque.

    prix_concurrent_moyen : prix moyen observé chez les concurrents
                            (0 = données non disponibles, pas d'ajustement)
    prix_de_base          : notre prix de base pour ce vol
    """
    if prix_concurrent_moyen <= 0 or prix_de_base <= 0:
        return 1.00

    ratio = prix_concurrent_moyen / prix_de_base

    if ratio < 0.65:   return 0.88   # concurrents très agressifs
    if ratio < 0.80:   return 0.94
    if ratio < 0.92:   return 0.98
    if ratio <= 1.10:  return 1.00   # parité → neutre
    if ratio <= 1.25:  return 1.04
    if ratio <= 1.45:  return 1.08
    return 1.12                       # on est bien moins chers → on monte


# ═════════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═════════════════════════════════════════════════════════════════════════════

def calculer_prix(
    prix_de_base: float,
    date_depart: datetime,
    date_calcul: datetime,
    taux_remplissage_vol: float,
    taux_remplissage_classe: float,
    classe: str,
    condition_meteo: ConditionMeteo = ConditionMeteo.NEUTRE,
    est_destination_soleil: bool = False,
    type_evenement: TypeEvenement = TypeEvenement.AUCUN,
    prix_concurrent_moyen: float = 0.0,
) -> dict:
    """
    Calcule le prix final ajusté et retourne le détail complet.

    Paramètres
    ----------
    prix_de_base              : prix de référence stocké dans la table vols
    date_depart               : datetime UTC du départ du vol
    date_calcul               : datetime UTC du moment de la recherche (now)
    taux_remplissage_vol      : 0.0 → 1.0, toutes classes confondues
    taux_remplissage_classe   : 0.0 → 1.0, spécifique à la classe demandée
    classe                    : 'eco' | 'business' | 'first'
    condition_meteo           : ConditionMeteo enum
    est_destination_soleil    : True si destination balnéaire/ski
    type_evenement            : TypeEvenement enum
    prix_concurrent_moyen     : prix moyen observé chez la concurrence (0 = N/A)

    Retourne
    --------
    dict avec :
        prix_de_base, prix_final, facteur_total, jours_avant,
        multiplicateurs (détail de chaque facteur), economie (± vs base)
    """
    jours_avant = max(0, (date_depart - date_calcul).days)

    multiplicateurs = {
        'remplissage':  multiplicateur_remplissage(taux_remplissage_vol, jours_avant),
        'anticipation': multiplicateur_anticipation(jours_avant),
        'saison':       multiplicateur_saison(date_depart),
        'jour_semaine': multiplicateur_jour_semaine(date_depart),
        'heure':        multiplicateur_heure(date_depart),
        'meteo':        multiplicateur_meteo(condition_meteo, est_destination_soleil),
        'evenement':    multiplicateur_evenement(type_evenement),
        'classe':       multiplicateur_classe(classe, taux_remplissage_classe),
        'concurrence':  multiplicateur_concurrence(prix_concurrent_moyen, prix_de_base),
    }

    facteur_total = math.prod(multiplicateurs.values())
    facteur_total = max(PRIX_MINIMUM_RATIO, min(PRIX_MAXIMUM_RATIO, facteur_total))

    prix_final = round(prix_de_base * facteur_total, 2)

    return {
        'prix_de_base':    prix_de_base,
        'prix_final':      prix_final,
        'facteur_total':   round(facteur_total, 4),
        'jours_avant':     jours_avant,
        'multiplicateurs': {k: round(v, 4) for k, v in multiplicateurs.items()},
        'economie':        round(prix_final - prix_de_base, 2),
    }


# ═════════════════════════════════════════════════════════════════════════════
# EXEMPLE D'INTÉGRATION DANS routes.py
# ═════════════════════════════════════════════════════════════════════════════
#
# from app.portail_admin.pricing import calculer_prix, ConditionMeteo, TypeEvenement
#
# resultat = calculer_prix(
#     prix_de_base             = vol.prix_de_base,
#     date_depart              = vol.date_heure_dep_utc,
#     date_calcul              = datetime.utcnow(),
#     taux_remplissage_vol     = nb_billets / capacite_totale,
#     taux_remplissage_classe  = billets_eco / capacite_eco,
#     classe                   = 'eco',
#     condition_meteo          = ConditionMeteo.BON,
#     est_destination_soleil   = True,
#     type_evenement           = TypeEvenement.AUCUN,
#     prix_concurrent_moyen    = 0.0,   # optionnel
# )
#
# prix_a_afficher = resultat['prix_final']
# ─────────────────────────────────────────────────────────────────────────────