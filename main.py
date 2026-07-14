if __name__ == "__main__":
    # 1. Charger la liste des Bauges
    df_bauges = load_communes()
    
    if df_bauges is not None:
        # 2. Enrichir avec le fichier INSEE (assurez-vous que le chemin est correct)
        path_insee = 'data/raw/insee_data.csv' 
        
        if os.path.exists(path_insee):
            df_final = enrichir_avec_insee(df_bauges, path_insee)
            print("Fusion réussie !")
            print(df_final.head())
            # Optionnel : sauvegarder le résultat
            df_final.to_csv('data/processed/communes_enrichies.csv', index=False)
        else:
            print(f"Attention : {path_insee} introuvable pour la fusion.")
