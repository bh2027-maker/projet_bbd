# BBD – Prospect Intelligence

## Problem Statement
Créer un **moteur intelligent de détection de prospects géographiques** pour la vente de pompes à chaleur air-eau (BAR-TH-171) dans le **Massif des Bauges**. Ce n'est pas un CRM, c'est un moteur de renseignement commercial : détecte → qualifie → classe → transmet. Question centrale : *"Quelles sont les meilleures maisons à visiter en priorité ?"*

Opération immédiate : préparer la tournée d'août du commercial Gaël (Services Energy 69). Commission partagée BBD ↔ Gaël.

## Users
- **BBD** — orchestre la campagne, priorise, transmet
- **Gaël** — commercial terrain qui reçoit les dossiers qualifiés

## Architecture
- **Backend** : FastAPI + MongoDB + httpx (Overpass, annuaire.service-public) + reportlab (PDF)
- **Frontend** : React 19 + Tailwind + shadcn/ui + react-leaflet (CartoDB dark)
- **IA** : Claude Sonnet 4.5 via clé Emergent
- **Sources externes** : geo.api.gouv.fr (INSEE, coords), Overpass API (footprints OSM/cadastre DGI), api-lannuaire.service-public.fr (mairies)

## What's Implemented

### Phase 1 (14/02) — Niveau COMMUNE
- Base des communes des Bauges < 2 500 hab, enrichie
- Moteur de scoring communal `/100` pondéré
- Dashboard + fiche commune + commentaire IA Claude

### Phase 2 (14/02) — Modules 2 + 7
- **Module 2** : recensement maison par maison via Overpass (filtre 55-500 m²), scoring individuel
- **Module 7** : pipeline prospect (7 statuts) + fiche prospect avec contact/notes
- Page /pipeline dédiée

### Phase 3 (14/02) — Modules 8 + Discovery masse + PDF
- **Fix critique** : les 20+ codes INSEE du seed étaient faux. Refactorisé pour utiliser geo.api.gouv.fr comme source de vérité (fichier `bauges_lookup.json`)
- **Module 8** : coordonnées mairie (nom, adresse, tél, email, site) via API annuaire.service-public.fr avec cache MongoDB
- **Lien Pages Jaunes** pré-rempli dans la fiche prospect
- **Discover All** : background task async qui lance Overpass sur toutes les communes sans maisons, avec suivi de progression en direct dans le dashboard
- **Feuille de route PDF** : `POST /api/tour/pdf` génère un PDF A4 dark theme avec :
  - Page couverture (nb prospects, distance totale, score moyen, top score, ordre de visite)
  - Optimisation nearest-neighbor (Haversine) partant du meilleur score
  - Une page par maison avec fiche complète, liens visuels (Google Maps, Street View, IGN), zone "Observations terrain" pour prendre des notes sur place
- Page /pipeline transformée : mode "Top 20 (toutes communes)" + sélection multi-checkbox + bouton PDF téléchargement

Testing agent Phase 3 : **100% pass** (backend 12/12, frontend complet).

Résultats en production (au moment de la livraison) :
- 25 communes seedées avec vrais codes INSEE
- 2 000+ maisons réelles déjà détectées (discovery des 25 communes en background)
- Top prospect détecté : maison de 178 m² à Aillon-le-Jeune, score 87.4

## Backlog

### P1 — Prochain sprint
- **Enrichissement bâti** : récupérer `start_date` réel via BD TOPO IGN (WFS) plutôt que fallback communal — améliore significativement le scoring anciennete
- **Filtres avancés page Pipeline** : par statut, par commune, par surface, tri
- **Export CSV** du pipeline (compatible Excel pour partage Gaël)
- Persister l'état de discovery-all dans MongoDB (résiste au restart backend)
- **Feuille de route par jour** : découper le top 20 en plusieurs journées avec plafond de distance

### P2
- **Module 9** : écosystème local (commerces, artisans, associations) via SIRENE / Google Places
- **Module 6 avancé** : intégration Google Street View embed (nécessite clé API)
- **Module 10** : recensement présences réseaux sociaux locales
- **Module 11** : dashboard commissions BBD / ventes / ROI par commune
- Historique/journal d'activité par maison

### P3
- Auth multi-utilisateur (BBD vs Gaël) avec permissions différentes
- Extension multi-territoires au-delà des Bauges
- Notifications push mobile pour changements de statut
