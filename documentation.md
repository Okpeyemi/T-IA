# Documentation Technique : API de Routage Bénin (T-IA)

## I. Introduction

### Contexte
Le projet s'inscrit dans le cadre du développement d'une solution de mobilité intelligente pour le Bénin. Les solutions de cartographie généralistes manquent souvent de contexte local (état des routes en saison des pluies, noms vernaculaires, coûts de transport informels).

### Objectif de la tâche
L'objectif est de fournir une API capable de calculer l'itinéraire optimal entre deux localités au Bénin, tout en enrichissant la réponse avec des données culturelles (traduction en Fon) et pratiques (impact météo, estimation coûts taxi/bus). Notre composant "Routing Engine" est le cœur de cette chaîne de valeur.

---

## II. Analyse de la tâche

### 2.1 Définition du problème
*   **Nature technique** : Il s'agit d'un problème de recherche de chemin (Pathfinding) dans un graphe pondéré, couplé à du géocodage inversé pour identifier les localités traversées.
*   **Contraintes identifiées** :
    *   **Qualité des données** : Les données OpenStreetMap (OSM) peuvent être incomplètes sur les vitesses.
    *   **Saisonnalité** : La saison des pluies dégrade significativement la vitesse sur les routes non bitumées.
    *   **Langue** : Nécessité de traduire les concepts de navigation en langue locale (Fon).

### 2.2 État de l'art
*   **Google Maps/Waze** : Très performants mais boîtes noires, coûteux et sans adaptations "hyper-locales" (prix zemidjan, saison des pluies).
*   **OSRM / Valhalla** : Moteurs de routage open-source très rapides (C++) mais complexes à déployer et à personnaliser pour des règles dynamiques (météo).
*   **Approche Retenue** : Utilisation de **OSMnx** et **NetworkX** en Python. Moins performant à très grande échelle que OSRM, mais offre une flexibilité totale pour manipuler le graphe (ajouter des pénalités météo dynamiquement).

---

## III. Choix de l'Architecture et de l'Approche

### 3.1 Modèle retenu
*   **Architecture** : API REST (FastAPI) exposant un moteur de calcul basé sur des graphes (NetworkX).
*   **Algorithme** : **Dijkstra Bidirectionnel**.

### 3.2 Justification du choix
*   **Pourquoi ce modèle ?** L'algorithme de Dijkstra garantit le chemin le plus court (ou le plus rapide). La version bidirectionnelle (recherche depuis le départ et l'arrivée simultanément) réduit l'espace de recherche, accélérant le calcul.
*   **Avantages** :
    *   **Flexibilité** : Permet de modifier les poids des arêtes (routes) à la volée selon la variable `season` (pluie/sec).
    *   **Précision** : Utilise les données réelles du réseau routier béninois (OSM).
    *   **Simplicité** : Facile à maintenir et à étendre en Python.

### 3.3 Méthodologie d'entrainement
*   *Non applicable* : Ce projet utilise une approche algorithmique déterministe et non un modèle d'apprentissage automatique (Machine Learning) nécessitant un entraînement. Les traductions sont effectuées via des mappages statiques pour une fiabilité maximale.

---

## IV. Présentation API

### 4.1 Description de l'endpoint
L'API expose un endpoint principal pour le calcul d'itinéraire.

*   **URL** : `POST /route`
*   **Exemple d'appel (cURL)** :
    ```bash
    curl -X 'POST' \
      'https://votre-api.onrender.com/route' \
      -H 'Content-Type: application/json' \
      -d '{
      "start": "Cotonou",
      "end": "Parakou",
      "season": "rain"
    }'
    ```

### 4.2 Format des requêtes et réponses

**Format d'entrée (JSON)** :
```json
{
  "start": "Ville de départ (ex: Cotonou)",
  "end": "Ville d'arrivée (ex: Parakou)",
  "avoid": "Ville à éviter (optionnel)",
  "season": "dry" ou "rain"
}
```

**Format de sortie (JSON)** :
```json
{
  "departure": "Kutɔnu (Cotonou)",
  "step_1": "Xɔgbonu (Porto-Novo) - 16.2km",
  "destination": "Parakou - 388.0km",
  "season": "Hwenu Jǐ",
  "info_sup": "Bǐ: 388km, ~7h49 | Bɔ̀s: ~6979F / Taxi: ~11632F"
}
```

**Gestion des erreurs** :
*   `400 Bad Request` : Si l'origine/destination est introuvable ou hors du Bénin.
*   `500 Internal Server Error` : En cas de problème technique lors du calcul.
