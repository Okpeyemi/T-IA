from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from core import calculate_route, RouteError

# Charger les variables d'environnement
load_dotenv()

app = FastAPI(
    title="Benin Routing API",
    description="API de calcul d'itinéraire au Bénin avec prise en compte de la saison et traduction Fon.",
    version="1.0.0"
)

# Modèle de requête
class RouteRequest(BaseModel):
    start: str
    end: str
    avoid: Optional[str] = None
    season: str = "dry"  # "dry" ou "rain"

# Endpoint principal
@app.post("/route")
async def get_route(request: RouteRequest):
    """
    Calcule l'itinéraire entre deux villes du Bénin.
    
    - **start**: Ville de départ (ex: "Cotonou")
    - **end**: Ville d'arrivée (ex: "Parakou")
    - **avoid**: Ville à éviter (ex: "Bohicon")
    - **season**: "dry" (sèche) ou "rain" (pluies)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    is_raining = (request.season.lower() == "rain")

    try:
        result = calculate_route(
            start_input=request.start,
            end_input=request.end,
            avoid_input=request.avoid,
            season_raining=is_raining,
            api_key=api_key
        )
        return result
    except RouteError as e:
        raise HTTPException(status_code=400, detail={"error": e.message, "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Erreur interne", "details": str(e)})

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API de routage Bénin 🇧🇯. Utilisez POST /route pour calculer un itinéraire."}
