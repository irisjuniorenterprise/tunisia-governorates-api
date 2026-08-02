# main.py - Version optimisée
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import Dict, Any
import json
import time
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

# Chargement optimisé
with open("tunisia.geojson", "r", encoding="utf-8") as f:
    GEOJSON_DATA = json.load(f)
    GOVERNORATES = [f["properties"]["gouv_fr"] for f in GEOJSON_DATA["features"]]
    # Index pour recherche rapide
    GOVERNORATE_INDEX = {g.lower(): g for g in GOVERNORATES}

# Métriques
class Metrics:
    def __init__(self):
        self.times = []
        self.count = 0
    def add(self, t):
        self.times.append(t); self.count += 1
        if len(self.times) > 1000: self.times.pop(0)
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
    return {"status": "healthy", "total": len(GOVERNORATES)}

@app.get("/api/governorates", tags=["Governorates"])
async def list_governorates():
    return {
        "count": len(GOVERNORATES),
        "governorates": [{"name": f["properties"]["gouv_fr"], "type": f["geometry"]["type"]} for f in GEOJSON_DATA["features"]]
    }

@app.get("/api/governorates/{name}", tags=["Governorates"])
async def get_governorate(name: str):
    if name.lower() not in GOVERNORATE_INDEX:
        raise HTTPException(404, f"Governorate '{name}' not found")
    for f in GEOJSON_DATA["features"]:
        if f["properties"]["gouv_fr"].lower() == name.lower():
            return f

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
        "samples": len(metrics.times)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)