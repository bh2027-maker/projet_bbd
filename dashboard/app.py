import streamlit as st
import pandas as pd

st.set_page_config(page_title="BBD - Prospect Intelligence", layout="wide")

st.title("🎯 BBD - Prospect Intelligence V1 (Massif des Bauges)")
st.caption("Moteur intelligent de détection de prospects PAC")

# Charger les données depuis processed/
@st.cache_data
def load_data():
    # Simulation des données issues du script de processed
    data = {
        "nom_commune": ["Bellecombe-en-Bauges", "Doucy-en-Bauges", "La Motte-en-Bauges", "Lescheraines"],
        "adresse": ["12 Rue du Centre", "5 Chef Lieu", "18 Route des Bauges", "2 Place de l'Église"],
        "annee_construction": [1985, 1992, 2008, 1974],
        "surface_m2": [120, 95, 110, 140],
        "chauffage_probable": ["fioul", "gaz", "electrique", "fioul"],
        "score_bbd": [98, 94, 46, 100],
        "lat": [45.741, 45.722, 45.701, 45.711],
        "lon": [6.142, 6.182, 6.128, 6.155]
    }
    return pd.DataFrame(data)

df = load_data()

# Filtres latéraux
st.sidebar.header("Filtres")
score_min = st.sidebar.slider("Score BBD Minimum", 0, 100, 80)

# Filtrer le DataFrame
df_filtered = df[df["score_bbd"] >= score_min].sort_values(by="score_bbd", ascending=False)

# Métriques rapides (Module 11)
col1, col2, col3 = st.columns(3)
col1.metric("Communes Détectées", len(df["nom_commune"].unique()))
col2.metric("Maisons Qualifiées (>80)", len(df[df["score_bbd"] >= 80]))
col3.metric("Prospects prioritaires", len(df_filtered))

st.subheader("📋 Liste des maisons qualifiées pour Gaël")

# Affichage du tableau avec lien Street View direct
for idx, row in df_filtered.iterrows():
    with st.expander(f"🏠 {row['adresse']}, {row['nom_commune']} — Score BBD : {row['score_bbd']}/100"):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write(f"**Année de construction :** {row['annee_construction']}")
            st.write(f"**Surface estimée :** {row['surface_m2']} m²")
            st.write(f"**Chauffage probable :** {row['chauffage_probable'].upper()}")
        with c2:
            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
            st.markdown(f"[🔍 Ouvrir Google Maps / Street View]({google_maps_url})", unsafe_allow_html=True)
            if st.button(f"Transmettre à Gaël ({row['adresse']})"):
                st.success("Dossier transmis !")

