from src.geodata import load_communes, calculer_indice_bbd

def main():
    df = load_communes()
    if df is not None:
        # Calculer le score et trier
        df_classe = calculer_indice_bbd(df)
        print("Classement des communes par potentiel BBD :")
        print(df_classe[['nom_commune', 'score_bbd']])

if __name__ == "__main__":
    main()
