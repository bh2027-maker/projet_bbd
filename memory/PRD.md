# BBD – Prospect Intelligence

## Problem Statement
Créer un **moteur intelligent de détection de prospects géographiques** pour la vente de pompes à chaleur air-eau (BAR-TH-171) dans le **Massif des Bauges**. Le logiciel n'est pas un CRM, c'est un moteur de renseignement commercial. Il doit répondre à une seule question : *"Quelles sont les meilleures maisons à visiter en priorité dans cette commune ?"*

Opération immédiate : préparer la tournée d'août du commercial Gaël (Services Energy 69). BBD détecte → qualifie → classe → transmet. Gaël vend. Commission partagée.

## User Personas
- **BBD (owner)** — prépare et priorise les dossiers en amont, orchestre la campagne.
- **Gaël (commercial terrain)** — reçoit les prospects triés, ne perd pas de temps à qualifier.

## Architecture
- **Backend** : FastAPI + MongoDB + httpx (Overpass), endpoints `/api/*`
- **Frontend** : React 19 + Tailwind + shadcn/ui + react-leaflet (dark CartoDB tiles)
- **IA** : Claude Sonnet 4.5 via clé Emergent universelle
- **Données externes** : Overpass API (OSM/cadastre DGI) pour les footprints de bâtiments
- **Design** : dark command-center, IBM Plex Sans/Mono, grid borders

## What's Implemented

### Phase 1 (14/02/2026) — Niveau COMMUNE
1. Base de 25 communes réelles du Massif des Bauges < 2 500 hab (Savoie + Haute-Savoie), enrichies (population, logements, revenu médian, altitude, GPS, zone H1)
2. Moteur de scoring communal `/100` pondéré (ancienneté 30%, maisons indiv. 20%, volume 20%, revenu 20%, climat 10%)
3. Dashboard dark command-center : 4 KPIs, carte react-leaflet, table classement 25 communes
4. Fiche commune détaillée avec breakdown score + **commentaire IA Claude Sonnet 4.5** (cached MongoDB)

### Phase 2 (14/02/2026) — Modules 2 + 7
5. **Module 2 — Recensement maison par maison** (`services/overpass.py`) : query Overpass API (User-Agent), filtre bâtiments 55-500 m² (plage typique maison indiv. FR), extrait footprint réel du cadastre DGI, calcule surface au sol + surface habitable estimée. Endpoint `POST /communes/{code}/discover`.
6. **Scoring individuel maison** (`services/house_scoring.py`) : score /100 par maison basé sur type OSM (house/detached/residential/yes), surface habitable, ancienneté (start_date OSM ou fallback commune), probabilité chauffage fossile, accessibilité (adresse), zone H1.
7. **Fiche prospect avec pipeline** (Module 7) : chaque maison a un statut (À analyser → À contacter → Intéressé → RDV → Transmis Gaël → Vendu / Perdu), notes libres, champs contact (nom/tel/email). Endpoint `PATCH /houses/{id}`.
8. **Page Pipeline global** (`/pipeline`) : kanban 7 colonnes avec counts + tableau des prospects actifs avec lien vers leur commune.
9. **Carte fiche commune** : leaflet zoomé sur la commune avec polygones réels de chaque maison colorés par score, clic → side panel (shadcn Sheet) avec breakdown, liens Google Maps / Street View / **IGN Orthophoto (Géoportail)**, dropdown statut, save.
10. **KPIs enrichis** : total maisons détectées, prospects actifs.

**Données réelles seedées** : Gruffy (500), Cusy (296), Bellecombe-en-Bauges (477) → **1 273 vraies maisons individuelles** en base, prêtes à qualifier.

Testing agent : **100% pass** (backend 10/10 + frontend complet).

## Backlog

### P1 — Prochain sprint
- **Feuille de route PDF quotidienne** pour Gaël (top 5 maisons du jour + itinéraire optimisé + fiches imprimables)
- Pré-lancer automatiquement `discover` sur les 25 communes (background job) pour éviter que le user clique 25 fois
- **Module 8** : enrichissement contacts via annuaires publics (pages jaunes, mairie), collecte semi-manuelle
- **Module 6** : Google Street View embed (nécessite clé API + budget)
- Export CSV du pipeline pour Gaël

### P2
- **Module 9** : écosystème local (commerces, artisans, associations) via SIRENE / Google Places
- **Module 10** : recensement présences réseaux sociaux locales (recensement uniquement, pas d'automation)
- **Module 11** : tableau de bord commissions / ventes / ROI par commune
- Enrichissement bâti : `start_date` réel via BD TOPO (IGN) plutôt que fallback commune
- Extension multi-territoires au-delà des Bauges (recharger la base communale + relancer Overpass)
- Filtres avancés (par statut, par score, par surface) sur la page pipeline

### P3
- Auth multi-utilisateur (Gaël vs BBD) avec permissions
- Notifications push quand une maison change de statut
- Historique/journal d'activité par maison
