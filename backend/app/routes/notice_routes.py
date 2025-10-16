from fastapi import APIRouter

router = APIRouter(prefix="/notices", tags=["notices"])

@router.get("/")
async def list_notices():
    return []
