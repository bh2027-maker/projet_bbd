# dashboard/app.py
import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="BBD - Prospect Intelligence", layout="wide")

st.title("🎯 BBD - Prospect Intelligence V1")
st.caption("Massif des Bauges — Prospection Pompes à Chaleur")

@st.cache_data
def load_data():
    path = "data/processed/maisons_qualifiees.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ Aucune donnée qualifiée disponible. Lance d'abord `python data/process_data.py`.")
else:
    # Sidebar - Filtres
    st.sidebar.header("🔍 Filtres Prospection")
    
    communes_dispo = ["Toutes"] + list(df["nom_commune"].unique())
    selected_commune = st.sidebar.selectbox("Commune", communes_dispo)
    
    min_score = st.sidebar.slider("Score BBD Minimum", 0, 100, 75)

    # Filtrage
    df_filtered = df[df["score_bbd"] >= min_score]
    if selected_commune != "Toutes":
        df_filtered = df_filtered[df_filtered["nom_commune"] == selected_commune]

    # KPI / Métriques (Module 11)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Communes", len(df["nom_commune"].unique()))
    col2.metric("Total Maisons", len(df))
    col3.metric("Prospects Prioritaires (≥75)", len(df[df["score_bbd"] >= 75]))
    col4.metric("Sélectionnés", len(df_filtered))

    st.divider()

    # Liste des fiches prospects (Module 7)
    st.subheader(f"📋 Fiches Prospects Qualifiés ({len(df_filtered)})")

    for idx, row in df_filtered.iterrows():
        score = row['score_bbd']
        badge_color = "🔴" if score < 50 else ("🟠" if score < 80 else "🟢")
        
        with st.expander(f"{badge_color} Score {score}/100 — {row['adresse']} ({row['nom_commune']})"):
            c1, c2, c3 = st.columns([2, 2, 1])
            
            with c1:
                st.write(f"**Commune :** {row['nom_commune']}")
                st.write(f"**Code Postal :** {row['code_post']}")
                st.write(f"**Chauffage estimé :** {str(row['type_chauffage_probable']).upper()}")

            with c2:
                st.write(f"**Année constr. estimée :** {row['annee_construction']}")
                st.write(f"**Surface estimée :** {row['surface_m2']} m²")
                st.write(f"**Statut :** {row.get('statut', 'À analyser')}")

            with c3:
                # Lien direct Google Street View (Module 6)
                lat, lon = row['lat'], row['lon']
                gmaps_url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
                st.markdown(f"[🔍 Street View]({gmaps_url})", unsafe_allow_html=True)
                
                if st.button("Transmettre à Gaël", key=f"btn_{idx}"):
                    st.success("Transmis !")
