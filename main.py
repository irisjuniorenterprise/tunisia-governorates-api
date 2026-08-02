# main.py - Version avec lecture depuis GitHub
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import Dict, Any
import json
import time
import os
import requests
from statistics import mean

# Configuration
app = FastAPI(
    title="Tunisia Governorates API",
    description="API de lecture des données géographiques des gouvernorats tunisiens",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse
)

# Middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ========== CHARGEMENT DES DONNÉES DEPUIS GITHUB ==========

GEOJSON_URL = "https://raw.githubusercontent.com/irisjuniorenterprise/tunisia-governorates-api/main/geojson/tunisia.geojson"

def load_geojson_from_github():
    """Charge le fichier GeoJSON depuis GitHub"""
    try:
        print(f"🔄 Loading GeoJSON from: {GEOJSON_URL}")
        response = requests.get(GEOJSON_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ GeoJSON loaded successfully: {len(data['features'])} features")
        return data
    except Exception as e:
        print(f"❌ Error loading from GitHub: {e}")
        # Fallback: essayer de charger depuis le système de fichiers local
        try:
            with open("geojson/tunisia.geojson", "r", encoding="utf-8") as f:
                print("✅ Loaded from local file as fallback")
                return json.load(f)
        except:
            print("❌ No local file found, using empty data")
            return {"features": []}

# Chargement des données
GEOJSON_DATA = load_geojson_from_github()
GOVERNORATES = [f["properties"]["gouv_fr"] for f in GEOJSON_DATA["features"]]
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
        "data_source": "GitHub",
        "data_loaded": len(GEOJSON_DATA["features"]) > 0
    }

@app.get("/api/governorates", tags=["Governorates"])
async def list_governorates():
    if not GEOJSON_DATA["features"]:
        raise HTTPException(503, "Data not loaded")
    return {
        "count": len(GOVERNORATES),
        "governorates": [
            {"name": f["properties"]["gouv_fr"], "type": f["geometry"]["type"]}
            for f in GEOJSON_DATA["features"]
        ]
    }

@app.get("/api/governorates/{name}", tags=["Governorates"])
async def get_governorate(name: str):
    if not GEOJSON_DATA["features"]:
        raise HTTPException(503, "Data not loaded")
    
    if name.lower() not in GOVERNORATE_INDEX:
        raise HTTPException(404, f"Governorate '{name}' not found")
    
    for f in GEOJSON_DATA["features"]:
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return f
    
    raise HTTPException(404, f"Governorate '{name}' not found")

@app.get("/api/governorates/{name}/properties", tags=["Governorates"])
async def get_properties(name: str):
    for f in GEOJSON_DATA["features"]:
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return {"name": f["properties"]["gouv_fr"], "properties": f["properties"]}
    raise HTTPException(404, f"Governorate '{name}' not found")

@app.get("/api/governorates/{name}/geometry", tags=["Governorates"])
async def get_geometry(name: str):
    for f in GEOJSON_DATA["features"]:
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return {"name": f["properties"]["gouv_fr"], "geometry": f["geometry"]}
    raise HTTPException(404, f"Governorate '{name}' not found")

@app.get("/api/search", tags=["Search"])
async def search(q: str, limit: int = 10):
    if not GEOJSON_DATA["features"]:
        raise HTTPException(503, "Data not loaded")
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)