# main.py (version initiale)
from fastapi import FastAPI

app = FastAPI(
    title="Tunisia Governorates API",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Tunisia Governorates API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)