
import pandas as pd
import os

def load_communes(filepath='data/raw/bauges_communes.csv'):
    """Charge la liste des communes depuis le CSV."""
    if not os.path.exists(filepath):
        print(f"Erreur : Le fichier {filepath} est introuvable.")
        return None
    
    df = pd.read_csv(filepath)
    print(f"Base chargée : {len(df)} communes détectées dans les Bauges.")
    return df

def enrichir_communes(df):
    """
    Ici, nous ajouterons plus tard les fonctions pour récupérer 
    les données INSEE (population, logements, etc.) via API.
    """
    # Exemple de structure ajoutée
    df['nb_habitants'] = 0
    df['nb_logements'] = 0
    return df


def enrichir_avec_insee(df_bauges, path_insee_csv):
    """
    Fusionne la base locale avec le dataset global INSEE
    path_insee_csv : chemin vers le fichier complet INSEE
    """
    df_insee = pd.read_csv(path_insee_csv, sep=';', dtype={'CODGEO': str})
    
    # On fait une jointure (Merge) sur le code commune
    df_final = pd.merge(df_bauges, df_insee, left_on='code_insee', right_on='CODGEO', how='left')
    
    return df_final


def calculer_indice_bbd(df):
    # Si la colonne n'existe pas, on met une valeur par défaut de 100 pour éviter le crash
    if 'nb_logements' not in df.columns:
        df['nb_logements'] = 100 
    
    df['score_bbd'] = df['nb_logements'] / 10 
    return df.sort_values(by='score_bbd', ascending=False)

def calculer_indice_bbd(df):
    """
    Calcule un score simple basé sur le nombre de logements.
    Plus il y a de logements, plus la commune est prioritaire.
    """
    # Exemple : Score = (Nombre de logements) / 10
    df['score_bbd'] = df['nb_logements'] / 10 
    return df.sort_values(by='score_bbd', ascending=False)

if __name__ == "__main__":
    data = load_communes()
    if data is not None:
        print(data.head())
