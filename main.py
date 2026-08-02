# main.py - Version robuste pour Vercel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import time
import requests
import os
from statistics import mean

app = FastAPI(
    title="Tunisia Governorates API",
    description="API de lecture des données géographiques des gouvernorats tunisiens",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== CHARGEMENT DES DONNÉES ==========

# Configuration de l'URL - AJUSTEZ LE NOM DE VOTRE REPO ET BRANCHE
GITHUB_USERNAME = "irisjuniorenterprise"  # ← CHANGEZ ICI SI NÉCESSAIRE
REPO_NAME = "tunisia-governorates-api"  # ← CHANGEZ ICI SI NÉCESSAIRE
BRANCH = "main"  # ou "master"
GEOJSON_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/{BRANCH}/geojson/tunisia.geojson"

def load_geojson():
    """Charge les données GeoJSON avec fallback"""
    print(f"📥 Loading GeoJSON from: {GEOJSON_URL}")
    
    # Essayer de charger depuis GitHub
    try:
        response = requests.get(GEOJSON_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("features") and len(data["features"]) > 0:
            print(f"✅ Loaded {len(data['features'])} features from GitHub")
            return data
    except Exception as e:
        print(f"❌ GitHub error: {e}")
    
    # Fallback: données minimales pour que l'API fonctionne
    print("⚠️ Using minimal fallback data")
    return {
        "type": "FeatureCollection",
        "features": []
    }

# Chargement au démarrage
GEOJSON_DATA = load_geojson()
GOVERNORATES = [f["properties"]["gouv_fr"] for f in GEOJSON_DATA.get("features", [])]
GOVERNORATE_INDEX = {g.lower(): g for g in GOVERNORATES}

print(f"📊 Loaded {len(GOVERNORATES)} governorates")

# ========== MÉTRIQUES ==========

class Metrics:
    def __init__(self):
        self.times = []
        self.count = 0
    def add(self, t):
        self.times.append(t)
        self.count += 1
        if len(self.times) > 1000:
            self.times.pop(0)
    def avg(self):
        return mean(self.times) if self.times else 0

metrics = Metrics()

@app.middleware("http")
async def track_time(request, call_next):
    start = time.time()
    response = await call_next(request)
    metrics.add(time.time() - start)
    response.headers["X-Process-Time"] = str(metrics.avg())
    return response

# ========== ENDPOINTS ==========

@app.get("/api/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "total": len(GOVERNORATES),
        "data_loaded": len(GEOJSON_DATA.get("features", [])) > 0
    }

@app.get("/api/governorates", tags=["Governorates"])
async def list_governorates():
    if not GOVERNORATES:
        return {"count": 0, "governorates": [], "message": "Data loading in progress"}
    return {
        "count": len(GOVERNORATES),
        "governorates": [
            {"name": f["properties"]["gouv_fr"], "type": f["geometry"]["type"]}
            for f in GEOJSON_DATA["features"]
        ]
    }

@app.get("/api/governorates/{name}", tags=["Governorates"])
async def get_governorate(name: str):
    if not GOVERNORATES:
        raise HTTPException(503, "Data not loaded yet")
    if name.lower() not in GOVERNORATE_INDEX:
        raise HTTPException(404, f"Governorate '{name}' not found")
    for f in GEOJSON_DATA["features"]:
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return f
    raise HTTPException(404, f"Governorate '{name}' not found")

@app.get("/api/governorates/{name}/properties", tags=["Governorates"])
async def get_properties(name: str):
    for f in GEOJSON_DATA.get("features", []):
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return {"name": f["properties"]["gouv_fr"], "properties": f["properties"]}
    raise HTTPException(404, f"Governorate '{name}' not found")

@app.get("/api/governorates/{name}/geometry", tags=["Governorates"])
async def get_geometry(name: str):
    for f in GEOJSON_DATA.get("features", []):
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return {"name": f["properties"]["gouv_fr"], "geometry": f["geometry"]}
    raise HTTPException(404, f"Governorate '{name}' not found")

@app.get("/api/search", tags=["Search"])
async def search(q: str, limit: int = 10):
    if not GOVERNORATES:
        return {"query": q, "count": 0, "results": []}
    results = []
    for f in GEOJSON_DATA["features"]:
        name = f["properties"]["gouv_fr"]
        if q.lower() in name.lower():
            results.append({"name": name, "type": f["geometry"]["type"]})
            if len(results) >= limit:
                break
    return {"query": q, "count": len(results), "results": results}

@app.get("/api/metrics", tags=["Metrics"])
async def get_metrics():
    return {
        "avg_response_ms": round(metrics.avg() * 1000, 2),
        "total_requests": metrics.count,
        "samples": len(metrics.times),
        "governorates_loaded": len(GOVERNORATES)
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# ========== POINT D'ENTRÉE POUR VERCEL ==========
# Vercel cherche 'app' par défaut
# 'app' est déjà défini ci-dessus

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)