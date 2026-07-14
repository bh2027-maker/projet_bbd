# BBD – Prospect Intelligence V1

## Problem Statement
Créer un **moteur intelligent de détection de prospects géographiques** pour la vente de pompes à chaleur air-eau (BAR-TH-171) dans le **Massif des Bauges**. Le logiciel n'est pas un CRM, c'est un moteur de renseignement commercial. Il doit répondre à une seule question : *"Quelles sont les meilleures communes à visiter en priorité ?"*

Opération immédiate : préparer la tournée d'août du commercial Gaël (Services Energy 69). Modèle : BBD détecte → qualifie → classe → transmet. Gaël vend. Commission partagée.

## User Personas
- **BBD (owner)** — prépare et priorise les dossiers en amont.
- **Gaël (commercial terrain)** — reçoit les communes triées, ne perd pas de temps à qualifier.

## Architecture
- **Backend** : FastAPI + MongoDB, endpoints /api/*
- **Frontend** : React 19 + Tailwind + shadcn/ui + react-leaflet (dark CartoDB tiles)
- **IA** : Claude Sonnet 4.5 via clé Emergent universelle (EMERGENT_LLM_KEY)
- **Design** : dark command-center, IBM Plex Sans/Mono, grid borders, score badges couleur

## What's Implemented (Phase 1 — 14/02/2026)
1. **Base géographique** : 25 communes réelles du Massif des Bauges (< 2500 hab), avec population, logements, maisons individuelles, revenu médian, altitude, GPS, zone climatique H1 (fichier `backend/bauges_data.py`).
2. **Moteur de scoring BBD** (`backend/scoring.py`) : score /100 pondéré sur 5 critères — ancienneté du parc (30%), part maisons individuelles (20%), volume (20%), revenu médian (20%), climat H1 (10%). Calcule aussi les dossiers BAR-TH-171 estimés.
3. **Dashboard** (`frontend/src/pages/Dashboard.jsx`) : 4 KPIs, carte react-leaflet interactive avec cercles colorés par score, table triable/filtrable des 25 communes avec recherche et slider score-min.
4. **Fiche commune détaillée** (`CommuneDetail.jsx`) : 3 cartes de données, décomposition du score critère par critère, **commentaire IA Claude Sonnet 4.5** avec cache MongoDB, lien Google Maps.
5. Endpoints backend : `/api/communes` (list + tri + filter), `/api/communes/{code}` (détail + rank), `/api/stats`, `/api/communes/{code}/ai-comment`, `/api/seed`.

Testing agent : **100% pass** backend + frontend.

## Backlog (Phase 2)
### P0 — Prochain sprint
- **Module 2** : recensement maison par maison (cadastre, adresses, GPS, parcelle) via IGN/API adresse.
- **Module 3-4** : score PAR MAISON (Module 3 : critères individuels ; Module 4 : score 0-100).
- **Module 7** : dossier prospect avec pipeline (À analyser → À contacter → RDV → Transmis Gaël → Vendu / Perdu).
- **Module 6** : intégration Google Maps / Street View directement dans la fiche.

### P1
- **Module 9** : écosystème local (commerces, artisans, associations) via SIRENE / Google Places.
- **Module 8** : contacts (nom, tel, mail) collectés publiquement.
- **Module 11** : tableau de bord commissions BBD / ventes.

### P2
- **Module 10** : recensement des présences réseaux sociaux locales.
- Extension multi-territoires (au-delà des Bauges).
- Export PDF fiche commune / fiche maison pour tournée terrain.

## Next Action Items
1. Valider avec l'utilisateur le classement des 25 communes livrées.
2. Enrichir la base avec les vraies données INSEE si besoin (actuellement estimations calibrées).
3. Attaquer Module 2 (recensement maisons) — c'est là que se joue la vraie valeur commerciale terrain.
