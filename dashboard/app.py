import streamlit as st
import pandas as pd
import os

# Configuration de la page
st.set_page_config(
    page_title="BBD - Prospect Intelligence",
    page_icon="🎯",
    layout="wide"
)

# Chargement des données qualifiées
@st.cache_data
def load_data():
    file_path = "data/processed/maisons_qualifiees.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return pd.DataFrame()

df = load_data()

# Titre de l'application
st.title("🎯 BBD - Prospect Intelligence V1")
st.markdown("### Massif des Bauges — Prospection Pompes à Chaleur")
st.write("---")

if df.empty:
    st.error("⚠️ Aucune donnée qualifiée disponible. Veuillez d'abord exécuter les scripts d'extraction et de scoring.")
else:
    # --- BARRE LATÉRALE DE FILTRES ---
    st.sidebar.header("🔍 Filtres de prospection")
    
    # Filtre par Commune
    communes = ["Toutes"] + sorted(df["nom_commune"].unique().tolist())
    commune_selected = st.sidebar.selectbox("Choisir une commune", communes)
    
    # Filtre par Score Minimum
    score_min = st.sidebar.slider("Score BBD Minimum", 0, 100, 75)
    
    # Application des filtres au DataFrame
    df_filtered = df[df["score_bbd"] >= score_min]
    if commune_selected != "Toutes":
        df_filtered = df_filtered[df_filtered["nom_commune"] == commune_selected]

    # --- EN-TÊTE DE KPIs ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Maisons Filtrées", len(df_filtered))
    with col2:
        prospects_chauds = len(df_filtered[df_filtered["score_bbd"] >= 80])
        st.metric("Prospects Très Chauds (Score ≥ 80)", prospects_chauds)
    with col3:
        score_moyen = round(df_filtered["score_bbd"].mean(), 1) if not df_filtered.empty else 0
        st.metric("Score BBD Moyen", f"{score_moyen}/100")

    st.write("---")

    # --- SECTION 2 : CARTE INTERACTIVE (NOUVEAU !) ---
    st.subheader("🗺️ Carte de Prospection Terrain")
    st.markdown("Visualisez l'emplacement des maisons cibles. Zoomez pour organiser la tournée de Gaël.")
    
    # Préparation des coordonnées pour st.map (nécessite des colonnes 'latitude' et 'longitude')
    df_map = df_filtered.copy()
    if not df_map.empty and "lat" in df_map.columns and "lon" in df_map.columns:
        df_map = df_map.rename(columns={"lat": "latitude", "lon": "longitude"})
        # Affichage de la carte
        st.map(df_map, latitude="latitude", longitude="longitude", size=15, color="#FF4B4B")
    else:
        st.info("Géolocalisation indisponible pour ces filtres.")

    st.write("---")

    # --- SECTION 3 : ACTIONS & EXPORTS (NOUVEAU !) ---
    st.subheader("📥 Actions & Export pour le Terrain")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        # Export au format Excel (idéal pour Gaël sur mobile / tablette)
        try:
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Prospects BBD')
            
            st.download_button(
                label="🟢 Télécharger la liste au format Excel",
                data=buffer.getvalue(),
                file_name=f"prospects_bbd_{commune_selected.lower().replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning("Export Excel indisponible. Utilisez l'export CSV.")

    with col_exp2:
        # Export au format CSV classique
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🔵 Télécharger la liste au format CSV",
            data=csv,
            file_name=f"prospects_bbd_{commune_selected.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )

    st.write("---")

    # --- SECTION 4 : FICHES PROSPECTS DETAILLES ---
    st.subheader(f"📋 Fiches des Prospects Qualifiés ({len(df_filtered)})")
    
    for idx, row in df_filtered.iterrows():
        # Détermination du badge de priorité
        score = row['score_bbd']
        if score >= 80:
            badge = "🔴 Priorité Très Haute"
        elif score >= 60:
            badge = "🟠 Priorité Moyenne"
        else:
            badge = "🟢 Priorité Modérée"
            
        with st.expander(f"{row['adresse']} ({row['nom_commune']}) — Score : {score}/100"):
            col_fiche1, col_fiche2 = st.columns(2)
            with col_fiche1:
                st.markdown(f"**Statut :** `{row.get('statut', 'À analyser')}`")
                st.markdown(f"**Priorité :** {badge}")
                st.markdown(f"**Année de construction :** {row.get('annee_construction', 'Inconnue')}")
                st.markdown(f"**Surface estimée :** {row.get('surface_m2', 'Inconnue')} m²")
                st.markdown(f"**Chauffage actuel :** {row.get('type_chauffage_probable', 'Inconnu')}")
            
            with col_fiche2:
                # Lien Street View
                lat, lon = row.get('lat'), row.get('lon')
                if lat and lon:
                    gmaps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    st.markdown(f"[👁️ Voir sur Google Maps / Street View]({gmaps_url})")
                
                # Bouton de transmission
                if st.button("📧 Envoyer cette fiche à Gaël", key=f"btn_{idx}"):
                    st.success(f"Fiche de l'adresse {row['adresse']} transmise avec succès à Gaël !")
