from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import re
import httpx
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from core import calculate_route_from_request, RouteError

WEBHOOK_URL = "http://91.99.208.100:8002"

# Charger les variables d'environnement
load_dotenv()

tags_metadata = [
    {
        "name": "Routage",
        "description": "Calcul d'itinéraires optimisés pour le Bénin.",
    },
    {
        "name": "General",
        "description": "Endpoints de base.",
    },
]

app = FastAPI(
    title="🇧🇯 Bénin Routing API",
    description="""
    API de calcul d'itinéraire intelligente pour le Bénin. 
    Intègre les contraintes locales :
    
    *   **Météo** : Ajustement du temps de trajet en saison des pluies.
    *   **Culture** : Traduction des étapes et conseils en Fon.
    *   **Contexte** : Suggestion de pause pour les longs trajets.
    """,
    version="1.1.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Support T-IA",
        "email": "support@t-ia.bj",
    }
)

# Sous-modèle des entités extraites par le NLP
class Entities(BaseModel):
    Departure: List[str] = Field(..., description="Ville(s) de départ détectées.")
    Destination: List[str] = Field(..., description="Ville(s) d'arrivée détectées.")
    Passengers: Optional[List[str]] = Field(None, description="Informations passagers (informatif).")

# Modèle de requête
class RouteRequest(BaseModel):
    text: str = Field(..., description="Phrase originale de l'utilisateur.")
    entities: Entities = Field(..., description="Entités extraites par le NLP.")

# Modèle de réponse pour la documentation
class RouteResponse(BaseModel):
    departure: str = Field(..., description="Lieu de départ formaté et traduit.")
    destination: str = Field(..., description="Lieu d'arrivée formaté et traduit.")
    season: str = Field(..., description="Saison courante traduite en Fon.")
    info_sup: str = Field(..., description="Résumé du trajet (distance, durée, coût estimé) traduit en Fon.")
    avoid_city: Optional[str] = Field(None, description="Ville évitée (si applicable).")
    
    # Pour les étapes dynamiques (step_1, step_2...), on utilise extra="allow" dans Pydantic
    # Mais pour OpenAPI, on peut être explicite si les clés étaient fixes.
    # Ici, comme les clés sont dynamiques (step_1, step_2...), on peut documenter cela dans la description.
    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "departure": "Cotonou",
                "step_1": "Porto-Novo - 16.2km",
                "step_2": "Sakete - 45.9km",
                "destination": "Parakou - 90.0km",
                "season": "Saison sèche",
                "info_sup": "Total: 388km, ~7h49 | Bus: ~6984F / Taxi: ~11640F"
            }
        }

@app.post(
    "/route", 
    response_model=RouteResponse, 
    tags=["Routage"],
    summary="Calculer un itinéraire",
    response_description="Itinéraire détaillé avec traduction Fon",
)
async def get_route(request: RouteRequest):
    """
    Calcule le meilleur itinéraire routier entre deux points au Bénin.
    
    Cette fonction prend en compte :
    - **L'état des routes** (basé sur OpenStreetMap)
    - **La saison** (impact sur les temps de trajet en cas de pluie)
    - **Les évitements** (contournement de villes spécifiques)
    
    Le résultat inclut une traduction en langue locale (Fon).
    """
    # Extraire le nombre de passagers depuis la chaîne (ex: "2 adultes" → 2)
    passengers = 1
    if request.entities.Passengers:
        match = re.search(r'\d+', request.entities.Passengers[0])
        if match:
            passengers = int(match.group())

    try:
        result = calculate_route_from_request({
            "departure":   request.entities.Departure[0],
            "destination": request.entities.Destination[0],
            "passengers":  passengers,
        })
    except RouteError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Erreur interne", "details": str(e)})

    payload = {"text": request.text, **result}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(WEBHOOK_URL, json=payload)
            logger.info("Webhook envoyé → %s | status: %d", WEBHOOK_URL, resp.status_code)
    except httpx.TimeoutException:
        logger.warning("Webhook timeout : %s n'a pas répondu dans les délais", WEBHOOK_URL)
    except httpx.RequestError as e:
        logger.error("Webhook inaccessible : %s", e)

    return result

@app.get("/", tags=["General"], include_in_schema=False)
def read_root():
    return {"message": "Bienvenue sur l'API de routage Bénin 🇧🇯. Allez sur /docs pour la documentation Swagger."}
