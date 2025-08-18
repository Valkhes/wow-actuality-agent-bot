from fastapi import FastAPI
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()

app = FastAPI(title="Discord Bot Health Check")


@app.get("/health")
async def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "discord-bot",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )


@app.get("/")
async def root():
    return {"message": "WoW Discord Bot is running"}