from src.geodata import load_communes, calculer_indice_bbd

def main():
    # 1. Chargement
    df = load_communes()
    
    if df is not None:
        print("Chargement réussi.")
        
        # 2. Calcul du score et classement (Module 5)
        df_classe = calculer_indice_bbd(df)
        
        # 3. Affichage du résultat pour Gaël
        print("--- Classement prioritaire des communes ---")
        print(df_classe[['nom_commune', 'score_bbd']])

if __name__ == "__main__":
    main()
