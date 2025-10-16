from fastapi import APIRouter

router = APIRouter(prefix="/uploads", tags=["uploads"])

@router.post("/")
async def upload_file():
    return {"message": "upload endpoint placeholder"}
