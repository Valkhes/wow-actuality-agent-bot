import structlog
import httpx
import asyncio
from typing import List, Dict, Optional, Union
from ..domain.entities import VectorDocument, AIResponse
from ..domain.repositories import AIRepository

logger = structlog.get_logger()


class LiteLLMAIRepository(AIRepository):
    """AI Repository using LiteLLM Gateway for secure LLM access"""
    
    def __init__(
        self,
        gateway_url: str,
        master_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        timeout: float = 30.0
    ):
        self.gateway_url = gateway_url.rstrip('/')
        self.master_key = master_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Create HTTP client
        headers = {
            "Content-Type": "application/json"
        }
        if master_key:
            headers["Authorization"] = f"Bearer {master_key}"
            
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=headers
        )
        
        self.system_message = """You are a helpful World of Warcraft news assistant. 
Your role is to provide accurate, up-to-date information about World of Warcraft based on the provided context.

Guidelines:
- Answer questions clearly and concisely
- Base your responses primarily on the provided context documents
- If the context doesn't contain relevant information, say so politely
- Keep responses under 500 words
- Focus on factual information about WoW news, updates, and changes
- Mention specific sources when relevant"""

    async def generate_response(
        self,
        question: str,
        context_documents: List[VectorDocument]
    ) -> AIResponse:
        """Generate AI response using LiteLLM Gateway"""
        
        logger.info(
            "Generating AI response via LiteLLM Gateway",
            question_length=len(question),
            context_docs_count=len(context_documents),
            gateway_url=self.gateway_url
        )
        
        try:
            # Prepare context from documents
            context_text = self._format_context(context_documents)
            
            # Prepare messages for LiteLLM
            messages = [
                {
                    "role": "system",
                    "content": self.system_message
                },
                {
                    "role": "user",
                    "content": f"""Context documents:
{context_text}

Question: {question}

Please provide a helpful response based on the context above."""
                }
            ]
            
            # Prepare request payload
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            
            logger.debug(
                "Sending request to LiteLLM Gateway",
                payload_size=len(str(payload)),
                model=self.model_name
            )
            
            # Make request to LiteLLM Gateway
            response = await self.client.post(
                f"{self.gateway_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Extract response content
            if "choices" in response_data and response_data["choices"]:
                content = response_data["choices"][0]["message"]["content"]
            else:
                raise ValueError("Invalid response format from LiteLLM Gateway")
            
            # Extract usage information if available
            usage_info = response_data.get("usage", {})
            if usage_info:
                logger.info(
                    "LLM usage information",
                    prompt_tokens=usage_info.get("prompt_tokens"),
                    completion_tokens=usage_info.get("completion_tokens"),
                    total_tokens=usage_info.get("total_tokens")
                )
            
            # Extract source articles with lower threshold to capture more relevant results
            source_articles = [
                doc.metadata.get("url", doc.metadata.get("title", f"Document {doc.id}"))
                for doc in context_documents
                if doc.metadata.get("similarity_score", 0) > 0.5  # Lower threshold from 0.7 to 0.5
            ]
            
            # Calculate confidence based on context relevance
            confidence = self._calculate_confidence(context_documents, question)
            
            ai_response = AIResponse(
                content=content,
                source_articles=source_articles,
                confidence=confidence
            )
            
            logger.info(
                "Successfully generated AI response via LiteLLM Gateway",
                response_length=len(ai_response.content),
                source_count=len(source_articles),
                confidence=confidence,
                tokens_used=usage_info.get("total_tokens", 0)
            )
            
            return ai_response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Security policy violation (prompt injection detected)
                logger.warning(
                    "Request blocked by LiteLLM Gateway security policy",
                    status_code=e.response.status_code,
                    question=question[:100]  # Log only first 100 chars for security
                )
                return AIResponse(
                    content="I cannot process this request due to security policy restrictions. Please rephrase your question.",
                    source_articles=[],
                    confidence=0.0
                )
            elif e.response.status_code == 429:
                # Rate limit exceeded
                logger.warning(
                    "Rate limit exceeded at LiteLLM Gateway",
                    status_code=e.response.status_code
                )
                return AIResponse(
                    content="I'm currently handling too many requests. Please try again in a moment.",
                    source_articles=[],
                    confidence=0.0
                )
            else:
                logger.error(
                    "HTTP error from LiteLLM Gateway",
                    status_code=e.response.status_code,
                    response_body=e.response.text[:200],
                    question=question[:100]
                )
                return self._fallback_response()
                
        except httpx.TimeoutException:
            logger.error(
                "Timeout error from LiteLLM Gateway",
                timeout=self.timeout,
                question=question[:100]
            )
            return self._fallback_response("The request is taking too long to process. Please try again.")
            
        except Exception as e:
            logger.error(
                "Unexpected error calling LiteLLM Gateway",
                error=str(e),
                error_type=type(e).__name__,
                question=question[:100],
                exc_info=True
            )
            return self._fallback_response()

    async def health_check(self) -> bool:
        """Check if LiteLLM Gateway is healthy"""
        try:
            response = await self.client.get(f"{self.gateway_url}/health")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.warning(
                "LiteLLM Gateway health check failed",
                error=str(e),
                gateway_url=self.gateway_url
            )
            return False

    async def get_security_config(self) -> Dict[str, Union[str, bool, int, float, List, Dict]]:
        """Get security configuration from LiteLLM Gateway"""
        try:
            response = await self.client.get(f"{self.gateway_url}/security/config")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(
                "Failed to get security config from LiteLLM Gateway",
                error=str(e)
            )
            return {}

    def _format_context(self, documents: List[VectorDocument]) -> str:
        """Format context documents for the LLM"""
        if not documents:
            return "No relevant context documents found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata
            title = metadata.get("title", f"Document {i}")
            url = metadata.get("url", "")
            similarity = metadata.get("similarity_score", 0)
            
            context_part = f"Document {i}: {title}"
            if url:
                context_part += f" (Source: {url})"
            if similarity:
                context_part += f" (Relevance: {similarity:.2f})"
            
            # Show more content - up to 1000 characters instead of 500
            content_preview = doc.content[:1000]
            if len(doc.content) > 1000:
                content_preview += "..."
            context_part += f"\nContent: {content_preview}\n"
            
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)

    def _calculate_confidence(self, documents: List[VectorDocument], question: str) -> float:
        """Calculate confidence score based on context documents and question"""
        if not documents:
            return 0.1
        
        # Calculate confidence based on:
        # 1. Number of relevant documents
        # 2. Average similarity score
        # 3. Question length (longer questions might be more specific)
        
        similarity_scores = [
            doc.metadata.get("similarity_score", 0.5)
            for doc in documents
        ]
        
        avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.5
        doc_count_factor = min(len(documents) / 3, 1.0)  # More docs = higher confidence, capped at 3
        question_factor = min(len(question) / 30, 1.0)  # Longer questions = higher confidence, capped at 30 chars
        
        confidence = (avg_similarity * 0.6) + (doc_count_factor * 0.3) + (question_factor * 0.1)
        
        return round(min(confidence, 0.95), 2)  # Cap at 95%

    def _fallback_response(self, message: str = None) -> AIResponse:
        """Return fallback response when LLM call fails"""
        default_message = "I'm sorry, I'm having trouble processing your question right now. Please try again in a moment."
        
        return AIResponse(
            content=message or default_message,
            source_articles=[],
            confidence=0.0
        )

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client"""
        await self.client.aclose()