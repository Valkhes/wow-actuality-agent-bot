#!/usr/bin/env python3
"""
LiteLLM Gateway with Prompt Injection Protection
Provides secure LLM access with monitoring and security middleware
"""

import os
import logging
from datetime import datetime

import uvicorn
import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import litellm

from config import MASTER_KEY, GOOGLE_API_KEY, LOG_LEVEL, ENVIRONMENT
from models import ChatCompletionRequest
from security import SecurityMiddleware
from handlers import (
    health_check,
    get_alerts,
    get_config,
    list_models,
    chat_completions
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Set up LiteLLM
litellm.set_verbose = True if LOG_LEVEL == "DEBUG" else False
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

app = FastAPI(
    title="WoW Actuality LiteLLM Gateway",
    description="Secure LLM Gateway with Prompt Injection Protection",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Apply security checks to all requests"""
    request_id = f"req_{datetime.utcnow().timestamp()}"
    client_id = request.client.host if request.client else "unknown"
    
    # Rate limiting
    if not SecurityMiddleware.check_rate_limit(client_id):
        SecurityMiddleware.log_security_alert(
            "HIGH",
            f"Rate limit exceeded for client {client_id}",
            request_id
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response


# Route definitions
app.get("/health")(health_check)
app.get("/security/alerts")(get_alerts)
app.get("/security/config")(get_config)
app.get("/models")(list_models)


@app.post("/chat/completions")
async def chat_completions_endpoint(request: ChatCompletionRequest, http_request: Request):
    client_host = http_request.client.host if http_request.client else "unknown"
    return await chat_completions(request, client_host)


if __name__ == "__main__":
    log_level = getattr(logging, LOG_LEVEL.upper())
    logging.basicConfig(level=log_level)
    
    logger.info(
        "starting_litellm_gateway",
        environment=ENVIRONMENT,
        log_level=LOG_LEVEL
    )
    
    port = int(os.environ.get("PORT", 4000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level=LOG_LEVEL.lower(),
        reload=ENVIRONMENT == "development"
    )