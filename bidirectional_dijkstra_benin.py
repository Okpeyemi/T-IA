import osmnx as ox
import networkx as nx
import heapq
import sys
import os
import reverse_geocoder as rg
import numpy as np

# --- 1. Chargement des données du graphe ---

def load_graph(place_name="Benin", filename="benin_major.graphml"):
    """
    Charge le graphe, assure que les vitesses et temps de trajet sont présents.
    """
    # Configuration
    ox.settings.use_cache = True
    ox.settings.log_console = False # Moins de bruit
    ox.settings.requests_timeout = 600

    if os.path.exists(filename):
        print(f"Chargement des données routières...")
        try:
            graph = ox.load_graphml(filename)
            return graph
        except Exception:
            pass # Si échec, on re-télécharge
    
    print(f"Téléchargement de la carte routière (Grands Axes) : {place_name}...")
    try:
        cf = '["highway"~"motorway|trunk|primary|secondary"]'
        graph = ox.graph_from_place(place_name, custom_filter=cf, network_type='drive')
        
        # Ajouter vitesses et temps (pour calculer le trajet le plus rapide)
        graph = ox.add_edge_speeds(graph)
        graph = ox.add_edge_travel_times(graph)
        
        ox.save_graphml(graph, filename)
        return graph
    except Exception as e:
        print(f"Erreur chargement graphe : {e}")
        return None

# --- 2. Dijkstra Bidirectionnel (Optimisé Temps ou Distance) ---

def bidirectional_dijkstra(graph, start_node, end_node, weight='travel_time', avoid_nodes=None):
    """
    Dijkstra Bidirectionnel.
    - weight: 'travel_time' (rapide) ou 'length' (court)
    - avoid_nodes: set des nœuds à éviter (interdits)
    """
    if avoid_nodes is None:
        avoid_nodes = set()
        
    if start_node not in graph or end_node not in graph:
        return None, float('inf')
        
    if start_node in avoid_nodes or end_node in avoid_nodes:
        # Impossible si départ ou arrivée est dans la zone interdite
        # On essaie quand même (l'utilisateur peut vouloir partir d'une ville qu'il veut éviter ?)
        # Mais techniquement pour le routage c'est un mur.
        # Pour être souple, on retire juste les nœuds d'évitement du graphe de recherche.
        pass

    q_f = [(0, start_node)]
    q_b = [(0, end_node)]
    
    dist_f = {start_node: 0}
    dist_b = {end_node: 0}
    
    parent_f = {start_node: None}
    parent_b = {end_node: None}
    
    visited_f = set()
    visited_b = set()
    
    mu = float('inf')
    meeting_node = None
    
    while q_f and q_b:
        if q_f[0][0] + q_b[0][0] >= mu:
            break
            
        # --- Forward ---
        if q_f:
            d_u, u = heapq.heappop(q_f)
            if u not in visited_f and u not in avoid_nodes:
                visited_f.add(u)
                for v in graph.neighbors(u):
                    if v in avoid_nodes: continue
                    
                    # Récupérer poids
                    edges = graph.get_edge_data(u, v)
                    # On prend l'arête qui minimise le critère (temps ou distance)
                    # Valeur par défaut infini si attribut manquant
                    val = min(d.get(weight, float('inf')) for d in edges.values())
                    
                    if d_u + val < dist_f.get(v, float('inf')):
                        dist_f[v] = d_u + val
                        parent_f[v] = u
                        heapq.heappush(q_f, (dist_f[v], v))
                        
                        if v in dist_b:
                            total = dist_f[v] + dist_b[v]
                            if total < mu:
                                mu = total
                                meeting_node = v

        # --- Backward ---
        if q_b:
            d_v, v = heapq.heappop(q_b)
            if v not in visited_b and v not in avoid_nodes:
                visited_b.add(v)
                for u in graph.predecessors(v):
                    if u in avoid_nodes: continue
                    
                    edges = graph.get_edge_data(u, v)
                    val = min(d.get(weight, float('inf')) for d in edges.values())
                    
                    if d_v + val < dist_b.get(u, float('inf')):
                        dist_b[u] = d_v + val
                        parent_b[u] = v
                        heapq.heappush(q_b, (dist_b[u], u))
                        
                        if u in dist_f:
                            total = dist_f[u] + dist_b[u]
                            if total < mu:
                                mu = total
                                meeting_node = u

    return reconstruct_path(parent_f, parent_b, meeting_node, mu)

def reconstruct_path(parent_f, parent_b, meeting_node, total_val):
    if meeting_node is None:
        return None, float('inf')
    
    # Reconstruct nodes
    path_f = []
    curr = meeting_node
    while curr is not None:
        path_f.append(curr)
        curr = parent_f[curr]
    path_f.reverse()
    
    path_b = []
    curr = parent_b[meeting_node]
    while curr is not None:
        path_b.append(curr)
        curr = parent_b[curr]
        
    return path_f + path_b, total_val

# --- 3. Logique d'Affichage Avancée ---

def get_path_metrics(graph, path_nodes):
    """Calcule distance totale (m) et temps total (s) pour un chemin donné."""
    total_dist = 0.0
    total_time = 0.0
    
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i+1]
        data = graph.get_edge_data(u, v)
        # On suppose qu'on a pris la meilleure arête. On prend le min travel_time pour être cohérent.
        # Idéalement faudrait stocker quelle clé d'arête on a utilisé, mais l'approximation suffit pour l'affichage global.
        edge = min(data.values(), key=lambda x: x.get('travel_time', float('inf')))
        
        total_dist += edge.get('length', 0)
        total_time += edge.get('travel_time', 0)
        
    return total_dist, total_time

def get_nodes_to_avoid(graph, city_name, radius_km=5):
    """Trouve tous les nœuds dans un rayon de X km autour d'une ville."""
    try:
        point = ox.geocode(f"{city_name}, Benin")
        # Trouver les nœuds dans le graphe qui sont proches de ce point
        # Pour faire simple avec osmnx : on cherche le nearest node, puis on fait un BFS/Dijkstra local 
        # pour trouver tous les nœuds à X mètres ? C'est lents.
        # Plus simple : itérer sur les nœuds et calculer la distance ? Lent aussi.
        # Meilleure option : ox.truncate.graph_from_point (mais on a déjà le graphe).
        
        # Approche simple et robuste : trouver le node le plus proche
        center_node = ox.distance.nearest_nodes(graph, point[1], point[0])
        
        # On interdit ce nœud et ses voisins à N degrés (ex: 2-3 sauts) ? 
        # Un rayon géographique est mieux. Mais complexe sans index spatial.
        
        # Pour une éviction efficace ("Éviter Bohicon"), il suffit de couper le carrefour principal.
        # On va identifier les 50 nœuds les plus proches pour être sûr de bloquer la traversée de la ville.
        # Attention c'est un hack, mais rapide.
        
        # Hack : On prend le centre, et on trouve les K nearest nodes (ex 50)
        # osmnx.distance.nearest_nodes(G, X, Y, return_dist=False) -> retourne 1 node.
        
        # On va utiliser une heuristique simple : bloquer un cercle autour du point géocodé.
        # Comme on a les coords dans graph.nodes[n]['x'] / ['y']
        
        avoid_set = set()
        c_lat, c_lon = point
        limit_sq = (radius_km / 111.0) ** 2 # Approx degrés (1 deg lat ~= 111km)
        
        for n, data in graph.nodes(data=True):
            dy = data['y'] - c_lat
            dx = data['x'] - c_lon
            if dy*dy + dx*dx < limit_sq:
                avoid_set.add(n)
                
        return avoid_set
    except Exception:
        return set()

# --- 4. Main ---

import json
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# --- Helper JSON ---
def print_json_error(msg, detail=None):
    err_dict = {"error": msg}
    if detail:
        err_dict["details"] = detail
    print("\n" + json.dumps(err_dict, indent=2, ensure_ascii=False))
    sys.exit(0)

# --- Configuration Gemini & Fon ---
FON_CITIES = {
    "Cotonou": "Kutɔnu",
    "Porto-Novo": "Xɔgbonu",
    "Abomey": "Agbomɛ",
    "Ouidah": "Glexwé",
    "Bohicon": "Bɔxikɔn",
    "Allada": "Alada"
}

import sys

def translate_with_gemini(text, api_key):
    if not api_key:
        return text
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (
            f"Translate the following text to Fon (Benin language). "
            f"Ensure to translate 'Total' to 'Bǐ' and 'Saison' to 'Hwenu'. "
            f"Translate 'Bus', 'Taxi', 'Suggestion' appropriately. "
            f"Keep numbers, prices, and special characters (like |) exactly as is. "
            f"Output ONLY the translated text, no markdown, no explanations. "
            f"Text: '{text}'"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Fallback silencieux en cas d'erreur API ou quota
        return text

def get_fon_city_name(city_fren):
    # Nettoyage basique pour matcher les clés
    base_name = city_fren.split(',')[0].strip()
    # Recherche case-insensitive
    for k, v in FON_CITIES.items():
        if k.lower() == base_name.lower():
            return f"{v} ({k})" # Format demandé : Fon (Français) ? Ou juste Fon ?
            # "Kutɔnu (Cotonou)" est demandé
    return city_fren

# --- 4. Main ---

if __name__ == "__main__":
    # On supprime le print d'intro pour ne pas polluer le JSON final si l'utilisateur parse stdout
    # print("\n--- 🇧🇯 Calcul d'itinéraire Expert (Temps/Coût/Saison) 🇧🇯 ---")
    
    start_input = input("Départ (ex: Cotonou, Ganhi) : ").strip() or "Cotonou"
    end_input = input("Arrivée (ex: Parakou, Lomé) : ").strip() or "Parakou"
    
    # 0. Validation : Origine/Destination identiques
    if start_input.lower() == end_input.lower():
        print_json_error(f"Origine et destination identiques ({start_input})")

    avoid_input = input("Éviter une ville ? : ").strip()
    saison_input = input("Saison (1=Sèche, 2=Pluies) [1] : ").strip()
    
    # On récupère la clé depuis l'environnement (.env ou export)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    # Si pas de clé, on pourrait demander, mais ici on assume que le .env est là.
    # if not gemini_key: gemini_key = input(...) 

    is_raining = (saison_input == "2")
    
    # 1. Chargement
    # Pour éviter les messages de chargement d'OSMnx dans le stdout, on peut rediriger stdout temporairement
    # mais c'est complexe. On suppose que l'utilisateur tolère les logs systèmes ou on a déjà ox.settings.log_console = False.
    G = load_graph()
    
    # 2. Points & Vérification Pays
    try:
        def smart_geocode(query):
            try:
                return ox.geocode(query)
            except:
                return ox.geocode(f"{query}, Benin")

        start_pt = smart_geocode(start_input)
        end_pt = smart_geocode(end_input)
        
        # Vérification International (Départ ET Arrivée)
        start_geocode_info = rg.search(start_pt)[0]
        dest_geocode_info = rg.search(end_pt)[0]
        
        start_cc = start_geocode_info['cc']
        dest_cc = dest_geocode_info['cc']
        
        # 1. Vérification du DÉPART
        if start_cc != 'BJ':
            print_json_error(
                f"Départ incorrect ({start_geocode_info['name']}, {start_cc})", 
                "La zone de couverture est EXCLUSIVEMENT le BÉNIN. Veuillez choisir une ville de départ au Bénin."
            )
            
        # 2. Vérification de l'ARRIVÉE
        if dest_cc != 'BJ':
            print_json_error(
                f"Destination hors zone ({dest_geocode_info['name']}, {dest_cc})", 
                "Trajet impossible : Le calculateur ne gère que les routes internes. PASSEPORT ou carnet CEDEAO requis."
            )
        
        start_node = ox.distance.nearest_nodes(G, start_pt[1], start_pt[0])
        end_node = ox.distance.nearest_nodes(G, end_pt[1], end_pt[0])
        
    except SystemExit:
        sys.exit(0)
    except Exception as e:
        print_json_error("Lieu introuvable", str(e))
        
    # 3. Évitement
    avoid_nodes = set()
    if avoid_input:
        # On pourrait logger ça en debug, mais pas en print principal
        avoid_nodes = get_nodes_to_avoid(G, avoid_input, radius_km=3) 

    # 4. Calcul
    # print("Calcul de l'itinéraire...") # Supprimé pour pureté JSON
    path, _ = bidirectional_dijkstra(G, start_node, end_node, weight='travel_time', avoid_nodes=avoid_nodes)
    
    if path:
        # --- Calcul des Segments pour le JSON ---
        coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in path]
        results = rg.search(coords)
        
        json_output = {}
        
        # Départ (Traduit si dans liste)
        start_city_res = results[0]['name'] # On prend le vrai nom géocodé ou l'input ?
        # L'user veut "Departure: Kutɔnu (Cotonou)"
        # On va essayer de mapper l'input utilisateur d'abord, sinon le géocodé
        real_start_name = start_input.title() # Ou results[0]['name']
        json_output["departure"] = get_fon_city_name(real_start_name)
        
        # Calcul des étapes et distances
        segment_dist = 0.0
        step_count = 1
        current_city_name = results[0]['name']
        
        # Identification Ville Finale
        final_city_name = None
        for res in reversed(results):
            if res['cc'] == 'BJ':
                final_city_name = res['name']
                break
        if not final_city_name: final_city_name = results[-1]['name']

        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            
            data = G.get_edge_data(u, v)
            edge_len = min(d.get('length', 0) for d in data.values())
            segment_dist += edge_len
            
            next_res = results[i+1]
            if next_res['cc'] != 'BJ': continue 
            
            next_city = next_res['name']
            
            if next_city != current_city_name:
                if next_city == final_city_name:
                    current_city_name = next_city
                else:
                    km_seg = segment_dist / 1000.0
                    city_fon = get_fon_city_name(next_city)
                    json_output[f"step_{step_count}"] = f"{city_fon} - {km_seg:.1f}km"
                    
                    step_count += 1
                    segment_dist = 0.0
                    current_city_name = next_city
        
        # Destination
        km_final = segment_dist / 1000.0
        dest_name_fon = get_fon_city_name(end_input.title())
        json_output["destination"] = f"{dest_name_fon} - {km_final:.1f}km"
        
        # --- Metadata (Saison / Evitement) ---
        if avoid_input:
            city_avoid_fon = get_fon_city_name(avoid_input.title())
            json_output["avoid_city"] = city_avoid_fon
        
        season_fr = "Saison des Pluies" if is_raining else "Saison Sèche"
        json_output["season"] = translate_with_gemini(season_fr, gemini_key)
        
        # --- Info Sup ---
        dist_m, time_s = get_path_metrics(G, path)
        km_total = dist_m / 1000.0
        
        # Météo
        weather_msg = ""
        lat_max = max(G.nodes[n]['y'] for n in path)
        if is_raining and lat_max > 9.8:
            time_s += 1800 # +30m
            weather_msg = " | [Météo] Route dégradée (+30min)"
            
        hours = int(time_s // 3600)
        minutes = int((time_s % 3600) // 60)
        duration_str = f"~{hours}h{minutes:02d}"
        
        # Suggestion
        sugg_msg = ""
        if hours >= 10:
            sugg_msg = " | Suggestion: découper en 2 jours"
            
        # Coûts
        p_bus = int(km_total * 18)
        p_taxi = int(km_total * 30)
        cost_msg = f" | Bus: ~{p_bus}F / Taxi: ~{p_taxi}F"
        
        info_sup_fr = f"Total: {km_total:.0f}km, {duration_str}{weather_msg}{cost_msg}{sugg_msg}"
        
        # Traduction Info Sup
        json_output["info_sup"] = translate_with_gemini(info_sup_fr, gemini_key)
        
        # Affichage JSON pur
        print("\n" + json.dumps(json_output, indent=2, ensure_ascii=False))
        
    else:
        print_json_error("Aucun chemin trouvé")
