from fastapi import APIRouter


router = APIRouter(prefix="/api")


@router.get("/status", tags=["status"])
async def api_status() -> dict[str, str]:
    return {"message": "CognitiveBrainDB API is running"}
