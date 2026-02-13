from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict
import os
from dotenv import load_dotenv

from core import calculate_route, RouteError

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

# Modèle de requête enrichi
class RouteRequest(BaseModel):
    start: str = Field(
        ..., 
        title="Ville de départ", 
        description="Nom de la ville ou du quartier de départ au Bénin.",
        examples=["Cotonou", "Ganhi"]
    )
    end: str = Field(
        ..., 
        title="Ville d'arrivée", 
        description="Nom de la ville ou du quartier d'arrivée au Bénin.",
        examples=["Parakou", "Tchaourou"]
    )
    avoid: Optional[str] = Field(
        None, 
        title="Ville à éviter", 
        description="Nom d'une ville à contourner (ex: travaux, bouchons).",
        examples=["Bohicon"]
    )
    season: str = Field(
        "dry", 
        title="Saison", 
        description="Saison actuelle pour ajuster les temps de trajet ('dry' = sèche, 'rain' = pluies).",
        pattern="^(dry|rain)$",
        examples=["dry"]
    )

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
                "departure": "Kutɔnu (Cotonou)",
                "step_1": "Xɔgbonu (Porto-Novo) - 16.2km",
                "step_2": "Sakete - 45.9km",
                "destination": "Parakou - 90.0km",
                "season": "Hwenu Gbigbɔn",
                "info_sup": "Bǐ: 388km, ~7h49 | Mɔ́tɔ́: ~6979F / Taxi: ~11632F"
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
    is_raining = (request.season.lower() == "rain")

    try:
        result = calculate_route(
            start_input=request.start,
            end_input=request.end,
            avoid_input=request.avoid,
            season_raining=is_raining
        )
        return result
    except RouteError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Erreur interne", "details": str(e)})

@app.get("/", tags=["General"], include_in_schema=False)
def read_root():
    return {"message": "Bienvenue sur l'API de routage Bénin 🇧🇯. Allez sur /docs pour la documentation Swagger."}
