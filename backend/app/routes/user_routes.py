from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def me():
    return {"user": "placeholder"}
