import pandas as pd
import os

def calculer_score_bbd(row):
    score = 0
    
    # 1. Ancienneté du bâtiment
    annee = row.get('annee_construction', 2005)
    if annee < 1980:
        score += 35
    elif annee < 2000:
        score += 25
    else:
        score += 5

    # 2. Surface estimée
    surface = row.get('surface_m2', 0)
    if surface >= 120:
        score += 25
    elif surface >= 90:
        score += 15
    else:
        score += 5

    # 3. Mode de chauffage probable
    chauffage = str(row.get('type_chauffage_probable', '')).lower()
    if 'fioul' in chauffage:
        score += 30
    elif 'gaz' in chauffage or 'charbon' in chauffage:
        score += 20
    elif 'electrique' in chauffage:
        score += 10

    # 4. Zone Climatique H1 (Bauges)
    score += 10

    return min(score, 100)

def process_pipeline():
    raw_path = "data/raw/maisons_raw.csv"
    output_path = "data/processed/maisons_qualifiees.csv"

    if not os.path.exists(raw_path):
        print(f"❌ Fichier introuvable : {raw_path}")
        return

    print("⏳ Chargement des maisons brutes...")
    df = pd.read_csv(raw_path)

    print("⚡ Calcul du Score BBD pour chaque maison...")
    df['score_bbd'] = df.apply(calculer_score_bbd, axis=1)
    df['statut'] = 'À analyser'
    df = df.sort_values(by='score_bbd', ascending=False)

    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(output_path, index=False)

    top_prospects = len(df[df['score_bbd'] >= 80])
    print(f"✅ Traitement terminé !")
    print(f"📊 Total maisons traitées : {len(df)}")
    print(f"🎯 Maisons très qualifiées (Score >= 80) : {top_prospects}")
    print(f"📁 Fichier sauvegardé : {output_path}")

if __name__ == "__main__":
    process_pipeline()