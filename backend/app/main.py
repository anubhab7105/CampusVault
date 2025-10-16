from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="CampusVault API")

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# static uploads (runtime)
app.mount("/uploads", StaticFiles(directory="app/static_uploads"), name="uploads")