# main.py

# Vous devez importer vos fonctions depuis votre dossier src
from src.geodata import load_communes, enrichir_avec_insee
import os

def main():
    # 1. Charger la liste
    df_bauges = load_communes()
    
    if df_bauges is not None:
        print("Chargement réussi.")
        # ... suite de votre logique
    else:
        print("Échec du chargement.")

if __name__ == "__main__":
    main()
