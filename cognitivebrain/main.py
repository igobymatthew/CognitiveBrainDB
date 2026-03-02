from fastapi import FastAPI

from cognitivebrain.api.routes import router as api_router
from cognitivebrain.config import settings


app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
