import pandas as pd
from config import (
    BONUS_ANCIENNETE_AVANT_2000,
    BONUS_SURFACE_SUP_90M2,
    BONUS_CHAUFFAGE_FIOUL_GAZ,
    BONUS_ZONE_CLIMATIQUE_H1
)

def calculer_score_maison(row):
    """
    Calcule le score BBD (sur 100) pour une maison individuelle
    """
    score = 0
    
    # Critère 1 : Ancienneté (Construit avant 2000)
    if row.get('annee_construction', 2005) < 2000:
        score += BONUS_ANCIENNETE_AVANT_2000
        
    # Critère 2 : Surface (> 90 m²)
    if row.get('surface_m2', 0) > 90:
        score += BONUS_SURFACE_SUP_90M2
        
    # Critère 3 : Probabilité Chauffage (Fioul / Gaz / Charbon)
    if row.get('type_chauffage_probable') in ['fioul', 'gaz', 'charbon']:
        score += BONUS_CHAUFFAGE_FIOUL_GAZ
        
    # Critère 4 : Zone climatique
    if row.get('zone_climatique') == 'H1':
        score += BONUS_ZONE_CLIMATIQUE_H1
        
    return min(score, 100)

def traiter_communes(file_path):
    df = pd.read_csv(file_path)
    df['score_bbd'] = df.apply(calculer_score_maison, axis=1)
    df = df.sort_values(by='score_bbd', ascending=False)
    return df
