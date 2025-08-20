"""
Configuration and constants for LiteLLM Gateway
Environment variables and security patterns
"""

import os
import re
from datetime import timedelta
from typing import List, Pattern

# Environment configuration
MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "your_master_key")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Rate limiting configuration
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW = timedelta(minutes=1)

# Security patterns for prompt injection detection
INJECTION_PATTERNS = [
    # Direct injection attempts
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)forget\s+(all\s+)?previous\s+instructions",
    r"(?i)disregard\s+(all\s+)?previous\s+instructions",
    r"(?i)override\s+(all\s+)?previous\s+instructions",
    
    # Role manipulation
    r"(?i)you\s+are\s+now\s+(a\s+)?different",
    r"(?i)pretend\s+(that\s+)?you\s+are",
    r"(?i)act\s+as\s+(a\s+)?different",
    r"(?i)roleplay\s+as",
    
    # System prompt leakage attempts
    r"(?i)what\s+(are\s+)?your\s+instructions",
    r"(?i)show\s+me\s+your\s+system\s+prompt",
    r"(?i)reveal\s+your\s+prompt",
    r"(?i)what\s+is\s+your\s+system\s+message",
    
    # Jailbreaking attempts
    r"(?i)developer\s+mode",
    r"(?i)jailbreak",
    r"(?i)demoralizing",
    r"(?i)unrestricted\s+mode",
    
    # Code execution attempts
    r"(?i)execute\s+code",
    r"(?i)run\s+python",
    r"(?i)import\s+os",
    r"(?i)subprocess\.run",
    
    # Suspicious tokens and patterns
    r"<\|.*?\|>",
    r"(?i)\\n\\n.*ignore",
    r"(?i)system:",
]

COMPILED_PATTERNS: List[Pattern] = [re.compile(pattern) for pattern in INJECTION_PATTERNS]