from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/history")
async def history():
    return []
