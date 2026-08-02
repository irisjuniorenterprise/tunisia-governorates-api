# main.py - Version avec endpoints de base
from fastapi import FastAPI, HTTPException, status
from typing import List, Dict, Optional
import json
import time
from statistics import mean

app = FastAPI(
    title="Tunisia Governorates API",
    description="API de lecture des données géographiques des gouvernorats tunisiens",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Chargement des données
try:
    with open("tunisia.geojson", "r", encoding="utf-8") as f:
        GEOJSON_DATA = json.load(f)
    GOVERNORATES = [feature["properties"]["gouv_fr"] for feature in GEOJSON_DATA["features"]]
except FileNotFoundError:
    print("⚠️  tunisia.geojson not found - using placeholder data")
    GEOJSON_DATA = {"features": []}
    GOVERNORATES = []

# Métriques
class PerformanceMetrics:
    def __init__(self):
        self.response_times = []
        self.request_count = 0
    def add_response_time(self, duration):
        self.response_times.append(duration)
        self.request_count += 1
        if len(self.response_times) > 1000:
            self.response_times.pop(0)
    def get_average(self):
        return mean(self.response_times) if self.response_times else 0.0

metrics = PerformanceMetrics()

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start = time.time()
    response = await call_next(request)
    metrics.add_response_time(time.time() - start)
    return response

@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "total_governorates": len(GOVERNORATES),
        "metrics": {
            "avg_response_ms": round(metrics.get_average() * 1000, 2),
            "total_requests": metrics.request_count
        }
    }

@app.get("/api/governorates", tags=["Governorates"])
async def list_governorates():
    return {
        "count": len(GOVERNORATES),
        "governorates": [
            {"name": f["properties"]["gouv_fr"], "type": f["geometry"]["type"]}
            for f in GEOJSON_DATA["features"]
        ]
    }

@app.get("/api/governorates/{name}", tags=["Governorates"])
async def get_governorate(name: str):
    for feature in GEOJSON_DATA["features"]:
        if feature["properties"]["gouv_fr"].lower() == name.lower():
            return feature
    raise HTTPException(status_code=404, detail=f"Governorate '{name}' not found")

# Ajout dans main.py
@app.get("/api/metrics", tags=["Metrics"])
async def get_metrics():
    return {
        "average_response_time_ms": round(metrics.get_average() * 1000, 2),
        "total_requests": metrics.request_count,
        "samples": len(metrics.response_times),
        "governorates_count": len(GOVERNORATES)
    }