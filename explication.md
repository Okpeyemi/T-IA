# Explication détaillée du code Bidirectional Dijkstra (Version Expert Bénin)

Ce document explique le fonctionnement du script `bidirectional_dijkstra_benin.py`. Il s'agit désormais d'un **calculateur d'itinéraire routier avancé** pour le Bénin, utilisant Dijkstra bidirectionnel sur données réelles (OSMnx).

## 1. Données Réelles & Optimisation (`load_graph`)

*   **Source** : OpenStreetMap (OSM) via la librairie `osmnx`.
*   **Filtre "Grands Axes"** : Seules les routes principales (`motorway`, `trunk`, `primary`, `secondary`) sont chargées pour garantir la rapidité.
*   **Persistance** : Le graphe est sauvegardé dans `benin_major.graphml` pour un démarrage instantané après le premier téléchargement.
*   **Données de Vitesse** : Le script ajoute automatiquement les vitesses (`speed`) et temps de trajet (`travel_time`) théoriques sur chaque segment de route.

## 2. Fonctionnalités "Expert"

Le script ne se contente plus de trouver le chemin le plus court en kilomètres. Il intègre maintenant plusieurs logiques métiers :

### A. Plus Rapide vs Plus Court
*   L'algorithme utilise le **Temps de trajet** (`travel_time`) comme poids des arêtes, et non plus la distance.
*   Cela favorise les routes nationales goudronnées (plus rapides) par rapport aux pistes raccourcies mais lentes.

### B. Évitement de Zone (`avoid_nodes`)
*   Si l'utilisateur demande d'éviter une ville (ex: "Bohicon"), le script identifie tous les nœuds routiers dans un **rayon de 3 km** autour du centre de cette ville.
*   Ces nœuds sont temporairement retirés du graphe ("murs invisibles"), forçant l'algorithme à trouver une déviation.

### C. Météo et État des Routes
*   **Saison des Pluies** : Si l'utilisateur sélectionne l'option "Saison des Pluies", le script analyse la latitude du trajet.
*   Si l'itinéraire monte au Nord du Bénin (> 9.8°N, vers Kandi/Malanville), il applique une **pénalité de temps (+30 min)** et affiche un avertissement `⚠️ État route: dégradé`.

### D. International (Lomé, Niamey...)
*   Le script détecte si la ville d'arrivée est hors du Bénin (`cc != 'BJ'`).
*   Il calcule l'itinéraire jusqu'au poste frontière le plus proche (ex: Hillacondji).
*   Il ajoute automatiquement l'alerte : `🛂 Docs requis: Passeport/CEDEAO`.

### E. Estimation des Coûts
*   Une estimation budgétaire est calculée basée sur la distance kilométrique :
    *   **Bus** : ~18 FCFA / km
    *   **Taxi** : ~30 FCFA / km

## 3. Géocodage et Affichage

*   **Smart Geocoding** : Gère les quartiers (ex: "Ganhi") en essayant d'abord la requête précise, puis en ajoutant ", Benin" si échec.
*   **Séquence de Villes** : Affiche la liste des villes traversées (ex: `Cotonou -> Calavi -> Bohicon -> Parakou`), en fusionnant les doublons consécutifs.
*   **Suggestions** : Si le trajet dépasse 10h de conduite, suggère : `Suggestion: découper en 2 jours`.

## 4. Algorithme (Dijkstra Bidirectionnel)

Le cœur mathématique reste inchangé : deux recherches simultanées (Départ->Arrivée et Arrivée->Départ) qui se rencontrent au milieu, garantissant l'optimalité du chemin tout en divisant drastiquement le temps de calcul.

---

### Fichiers du projet
*   `bidirectional_dijkstra_benin.py` : Script principal (Version Expert).
*   `benin_major.graphml` : Données cartographiques (Ne pas supprimer).

## 5. Détail des Fonctions (Structure du Code)

Voici le rôle précis de chaque bloc de code :

### `load_graph(place_name, filename)`
*   **Rôle** : Gère l'acquisition des données cartographiques.
*   **Détail** : Vérifie si le fichier `.graphml` existe. Sinon, télécharge depuis OSM avec un filtre sur les routes principales (`motorway` à `secondary`). Ajoute les attributs `speed` et `travel_time` aux arêtes.

### `bidirectional_dijkstra(graph, start, end, weight, avoid_nodes)`
*   **Rôle** : Le moteur de recherche de chemin.
*   **Détail** : Lance deux explorations (une depuis le départ, une depuis l'arrivée). À chaque étape, explore le voisin le plus proche. Si un nœud est dans `avoid_nodes`, il est ignoré (comme s'il n'existait pas). La recherche s'arrête quand les deux fronts se touchent.

### `reconstruct_path(parent_f, parent_b, meeting_node, ...)`
*   **Rôle** : Reconstruit l'itinéraire complet.
*   **Détail** : Une fois que les deux recherches se sont rencontrées, cette fonction remonte la piste des parents vers le début (`path_f`) et vers la fin (`path_b`), puis colle les deux morceaux.

### `get_path_metrics(graph, path_nodes)`
*   **Rôle** : Calculateur de statistiques.
*   **Détail** : Parcourt la liste finale des nœuds pour sommer précisement les distances (mètres) et les temps (secondes) de chaque segment de route emprunté.

### `get_nodes_to_avoid(graph, city_name, radius_km)`
*   **Rôle** : Générateur de "Murs".
*   **Détail** : Géocode la ville à éviter, puis identifie tous les nœuds routiers dans un rayon donné (ex: 3km). Retourne un ensemble (`set`) de ces nœuds interdits.

### `smart_geocode(query)`
*   **Rôle** : Aide à la saisie.
*   **Détail** : Tente de trouver le lieu tel quel. Si ça échoue, ajoute le suffixe ", Benin" et réessaie. Cela permet de taper juste "Cotonou" ou "Parakou, Benin" indifféremment.

### `Bloc Main (__name__ == "__main__")`
*   **Rôle** : Orchestrateur (Chef d'orchestre).
*   **Détail** :
    1.  Récupère les saisies utilisateur (Villes, Saison...).
    2.  Valide les entrées (Erreur si Départ = Arrivée).
    3.  Appelle `load_graph` et calcule les nœuds départ/arrivée.
    4.  Lance `bidirectional_dijkstra` avec les bonnes options (évitement, poids temporel).
    5.  Applique les règles métiers finales (Météo, Frontières, Prix) et formate l'affichage.
