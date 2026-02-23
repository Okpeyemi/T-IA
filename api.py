from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import os
from dotenv import load_dotenv

from core import calculate_route_from_request, RouteError

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
    *   **Contexte** : Suggestion de pause pour les longs trajets.
    """,
    version="1.1.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Support T-IA",
        "email": "support@t-ia.bj",
    }
)

# Modèle de requête
class RouteRequest(BaseModel):
    text: str = Field(..., description="Phrase originale de l'utilisateur.")
    departure: str = Field(..., description="Ville de départ.", examples=["Cotonou"])
    destination: str = Field(..., description="Ville d'arrivée.", examples=["Parakou"])

# Modèle de réponse pour la documentation
class RouteResponse(BaseModel):
    text: str = Field(..., description="Phrase originale de l'utilisateur.")
    departure: str = Field(..., description="Lieu de départ.")
    destination: str = Field(..., description="Lieu d'arrivée.")
    season: str = Field(..., description="Saison courante.")
    info_sup: str = Field(..., description="Résumé du trajet (distance, durée, coût estimé).")
    avoid_city: Optional[str] = Field(None, description="Ville évitée (si applicable).")

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "text": "Cotonou-Parakou demain à 8h",
                "departure": "Cotonou",
                "step_1": "Porto-Novo - 16.2km",
                "step_2": "Sakete - 45.9km",
                "destination": "Parakou - 388.0km",
                "season": "Saison sèche",
                "info_sup": "Total: 388km, ~7h49 | Bus: ~6984F / Taxi: ~11640F"
            }
        }

@app.post(
    "/route",
    response_model=RouteResponse,
    tags=["Routage"],
    summary="Calculer un itinéraire",
    response_description="Itinéraire détaillé",
)
async def get_route(request: RouteRequest):
    """
    Calcule le meilleur itinéraire routier entre deux points au Bénin.

    - **L'état des routes** (basé sur OpenStreetMap)
    - **La saison** (impact sur les temps de trajet en cas de pluie)
    - **Les évitements** (contournement de villes spécifiques)
    """
    try:
        result = calculate_route_from_request({
            "departure":   request.departure,
            "destination": request.destination,
        })
    except RouteError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Erreur interne", "details": str(e)})

    result["text"] = request.text
    return result

@app.get("/", tags=["General"], include_in_schema=False)
def read_root():
    return {"message": "Bienvenue sur l'API de routage Bénin 🇧🇯. Allez sur /docs pour la documentation Swagger."}
