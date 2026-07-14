# BBD – Prospect Intelligence

## Problem Statement
Moteur intelligent de détection de prospects géographiques pour la vente de pompes à chaleur (BAR-TH-171) dans le Massif des Bauges. Non-CRM : détecte → qualifie → classe → transmet. Répond à : *"Quelles sont les meilleures maisons à visiter en priorité ?"*

## Users
- **BBD** — orchestre, priorise, transmet
- **Gaël** — commercial terrain, tournée d'août

## Architecture
- **Backend** : FastAPI + MongoDB + httpx + reportlab + emergentintegrations (Claude)
- **Frontend** : React 19 + Tailwind + shadcn/ui + react-leaflet
- **APIs externes** :
  - geo.api.gouv.fr → codes INSEE, coordonnées, populations
  - Overpass API (OSM/cadastre DGI) → footprints des bâtiments
  - IGN BD TOPO WFS (data.geopf.fr) → dates de construction réelles, hauteurs, matériaux, logements
  - api-lannuaire.service-public.fr → coordonnées mairies
  - recherche-entreprises.api.gouv.fr (SIRENE) → écosystème local
  - Emergent Universal Key → Claude Sonnet 4.5 (commentaires IA)

## What's Implemented

### Phase 1 — Niveau COMMUNE
Base 25 communes des Bauges + scoring communal + dashboard + fiche commune + commentaire IA Claude.

### Phase 2 — Modules 2 + 7
Recensement maison par maison via Overpass, scoring individuel, pipeline prospect avec 7 statuts, side-panel HouseSheet, page /pipeline.

### Phase 3 — Modules 8 + Discovery masse + PDF
Fix codes INSEE via geo.api.gouv.fr. Mairie (Module 8) avec cache. Discover All background async. Feuille de route PDF (reportlab + nearest-neighbor Haversine).

### Phase 4 — BD TOPO + Filtres + Module 9
- **Enrichissement BD TOPO IGN** (`services/bdtopo.py`) : matching centroïde tolérance 15m, récupère `date_d_apparition`, `hauteur`, `nombre_d_etages`, `nombre_de_logements`, `usage`, `matériaux`. Endpoint `POST /enrichment/start` + suivi progression. **Résultat en prod : 4 059 maisons matched (97%), 2 201 dates de construction réelles injectées (54%)**. Score maximum passé de 87.4 → **92.7** grâce aux vraies dates.
- **Filtres avancés Pipeline** : par statut (multi), par commune (multi), par score min, par surface min. Compteur d'actifs dans le bouton.
- **Export CSV** (Excel FR, séparateur `;`, BOM UTF-8) : 17 colonnes incluant contact, GPS, lien Google Maps direct, notes.
- **Module 9 Écosystème local** (`services/sirene.py`) : 7 catégories NAF (Artisans BTP, Commerces, Restauration, Auto/moto, Bricolage/agricole, Santé, Associations). Endpoint `/communes/{code}/ecosysteme` avec cache. Card dans la fiche commune avec accordéons. **Résultat Gruffy : 39 entités locales identifiées, dont 24 artisans BTP avec noms/adresses complètes**.

Testing agent Phase 4 : **100% pass** (backend 8/8 + frontend complet).

## Production state (livraison)
- 25 communes seedées, vrais codes INSEE
- **4 175 maisons individuelles** réelles détectées (OSM/cadastre DGI)
- **2 201 avec dates de construction réelles** (BD TOPO IGN)
- Top prospect : maison **258.8 m² au Châtelard, score 92.7**
- Contacts mairies + écosystèmes locaux disponibles à la demande

## Backlog

### P1 — Prochain sprint
- **Calcul CEE théorique par maison** dans le PDF (formule BAR-TH-171 × prix marché) → outil d'argumentation client sur le pas de porte
- **Découpage tournée multi-journées** (feuille de route par jour avec plafond de distance)
- **Persister état discover/enrichment dans MongoDB** (résiste au restart backend)
- Vraies photos satellites IGN embarquées dans le PDF (WMTS ortho tiles)

### P2
- **Module 6 avancé** : Street View embed (nécessite clé Google Maps + budget)
- **Module 10** : recensement présences réseaux sociaux (Facebook groupes, Instagram hashtags)
- **Module 11** : dashboard commissions BBD / ROI par commune
- **Enrichissement bâti supplémentaire** : matériaux traduits (codes IGN → mur pierre/béton, toit tuile/ardoise…)
- Historique/journal d'activité par maison + notifications changement statut

### P3
- Auth multi-utilisateur (BBD vs Gaël) avec permissions
- Extension multi-territoires au-delà des Bauges
- Notifications push mobile
