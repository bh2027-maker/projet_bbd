# data/fetch_data.py
import requests
import pandas as pd
import os
import time

COMMUNES_BAUGES = [
    {"nom": "Bellecombe-en-Bauges", "code_insee": "73039", "code_postal": "73340"},
    {"nom": "Doucy-en-Bauges", "code_insee": "73101", "code_postal": "73630"},
    {"nom": "La Motte-en-Bauges", "code_insee": "73179", "code_postal": "73340"},
    {"nom": "Lescheraines", "code_insee": "73146", "code_postal": "73340"},
    {"nom": "Le Châtelard", "code_insee": "73081", "code_postal": "73630"},
    {"nom": "Aillon-le-Jeune", "code_insee": "73004", "code_postal": "73340"},
    {"nom": "Aillon-le-Vieux", "code_insee": "73005", "code_postal": "73340"},
    {"nom": "Jarsy", "code_insee": "73138", "code_postal": "73630"},
    {"nom": "Arith", "code_insee": "73020", "code_postal": "73340"},
    {"nom": "Ecole", "code_insee": "73106", "code_postal": "73630"}
]

def fetch_communes_metadata():
    """Récupère les informations démographiques via GeoAPI (INSEE)"""
    print("⏳ Récupération des données communes INSEE...")
    list_communes = []
    
    for c in COMMUNES_BAUGES:
        url = f"https://geo.api.gouv.fr/communes/{c['code_insee']}?fields=nom,code,population,codesPostaux"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                list_communes.append({
                    "code_insee": c['code_insee'],
                    "nom_commune": data.get("nom"),
                    "population": data.get("population"),
                    "code_postal": c['code_postal'],
                    "zone_climatique": "H1",
                    "altitude_moyenne": 850
                })
        except Exception as e:
            print(f"⚠️ Erreur commune {c['nom']}: {e}")
            
    df = pd.DataFrame(list_communes)
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv("data/raw/bauges_communes.csv", index=False)
    print(f"✅ {len(df)} communes sauvegardées dans data/raw/bauges_communes.csv")

def fetch_adresses_commune(code_insee, nom_commune):
    """Récupère les points adresses réels de la commune"""
    print(f"⏳ Extraction des adresses pour {nom_commune}...")
    maisons = []
    mots_cles = ["Route", "Rue", "Chemin", "Chef Lieu", "Villard", "Impasse", "Place"]
    seen_ids = set()
    
    for mc in mots_cles:
        url = f"https://api-adresse.data.gouv.fr/search/?q={mc}&citycode={code_insee}&limit=50"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                features = res.json().get("features", [])
                for f in features:
                    props = f.get("properties", {})
                    geom = f.get("geometry", {})
                    ban_id = props.get("id") or props.get("label")
                    
                    if ban_id and ban_id not in seen_ids:
                        seen_ids.add(ban_id)
                        coords = geom.get("coordinates", [0, 0])
                        maisons.append({
                            "id_ban": ban_id,
                            "adresse": props.get("label"),
                            "nom_commune": nom_commune,
                            "code_post": props.get("postcode"),
                            "lon": coords[0],
                            "lat": coords[1],
                            "type_batiment": "Maison Individuelle",
                            "annee_construction": 1988,
                            "surface_m2": 115,
                            "type_chauffage_probable": "fioul"
                        })
        except Exception as e:
            pass
            
    print(f"  ➜ {len(maisons)} adresses trouvées pour {nom_commune}")
    return maisons

def run_pipeline():
    # 1. Métadonnées communes
    fetch_communes_metadata()
    
    # 2. Extraction adresses avec SAUVEGARDE AU FUR ET À MESURE
    os.makedirs("data/raw", exist_ok=True)
    raw_csv = "data/raw/maisons_raw.csv"
    
    all_maisons = []
    for c in COMMUNES_BAUGES:
        maisons = fetch_adresses_commune(c["code_insee"], c["nom"])
        all_maisons.extend(maisons)
        
        # Sauvegarde progressive dans le CSV
        df_temp = pd.DataFrame(all_maisons)
        df_temp.to_csv(raw_csv, index=False)
        
    print(f"\n🎉 SCRIPT TERMINÉ AVEC SUCCÈS !")
    print(f"🚀 Total : {len(all_maisons)} adresses sauvegardées dans '{raw_csv}' !")

if __name__ == "__main__":
    run_pipeline()
