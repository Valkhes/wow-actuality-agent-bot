"""
Route handlers for LiteLLM Gateway
API endpoints and request processing
"""

import structlog
from datetime import datetime
from fastapi import HTTPException
from litellm import completion

from models import ChatCompletionRequest
from security import SecurityMiddleware, get_security_alerts, get_security_config

logger = structlog.get_logger()


async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


async def get_alerts():
    """Get recent security alerts"""
    alerts = get_security_alerts()
    return {
        "alerts": [alert.dict() for alert in alerts],
        "total_count": len(alerts)
    }


async def get_config():
    """Get current security configuration"""
    return get_security_config()


async def list_models():
    """List available models"""
    return {
        "models": [
            {
                "id": "gemini/gemini-2.0-flash-exp",
                "object": "model",
                "created": int(datetime.utcnow().timestamp()),
                "owned_by": "google",
                "permission": [],
                "root": "gemini-2.0-flash-exp",
                "parent": None
            }
        ]
    }


async def chat_completions(request: ChatCompletionRequest, client_host: str):
    """
    Chat completions endpoint with prompt injection protection
    """
    request_id = f"chat_{datetime.utcnow().timestamp()}"
    
    try:
        # Security check: Detect prompt injection in user messages
        for message in request.messages:
            if message.role == "user":
                injection_pattern = SecurityMiddleware.detect_prompt_injection(message.content)
                if injection_pattern:
                    SecurityMiddleware.log_security_alert(
                        "HIGH",
                        f"Prompt injection detected: {injection_pattern}",
                        request_id
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Request blocked due to security policy violation"
                    )
        
        # Convert messages to LiteLLM format
        litellm_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        logger.info(
            "llm_request",
            request_id=request_id,
            model=request.model,
            message_count=len(litellm_messages),
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Make LLM call
        response = await completion(
            model=request.model,
            messages=litellm_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )
        
        logger.info(
            "llm_response",
            request_id=request_id,
            model=request.model,
            usage=response.get("usage", {})
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "llm_error",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )