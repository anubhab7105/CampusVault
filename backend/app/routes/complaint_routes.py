from fastapi import APIRouter

router = APIRouter(prefix="/complaints", tags=["complaints"])

@router.post("/")
async def submit_complaint():
    return {"status": "received"}
