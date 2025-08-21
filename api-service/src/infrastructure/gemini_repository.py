import structlog
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from ..domain.entities import VectorDocument, AIResponse
from ..domain.repositories import AIRepository

logger = structlog.get_logger()


class GeminiAIRepository(AIRepository):
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Focused prompt template that emphasizes using the best single source
        self.prompt_template = """Answer this question about World of Warcraft: {question}

Use this information to help answer:
{context}

IMPORTANT INSTRUCTIONS:
- Focus your answer on the MOST RELEVANT document that best answers the question
- Provide a precise, accurate answer based primarily on that single best source
- Be concise and specific rather than trying to combine multiple sources
- ALWAYS include the source article URL at the end of your response from the most relevant document
- Use the format: Source: [URL]"""

    async def generate_response(
        self,
        question: str,
        context_documents: List[VectorDocument]
    ) -> AIResponse:
        
        logger.info(
            "Generating AI response with Gemini",
            question_length=len(question),
            context_docs_count=len(context_documents)
        )
        
        try:
            # Prepare context from documents
            context_text = self._format_context(context_documents)
            
            # Debug: Log context and question for debugging
            logger.info(
                "Debug - Context and question for Gemini",
                context_preview=context_text[:300] if context_text else "No context",
                question=question,
                context_length=len(context_text) if context_text else 0
            )
            
            # Format the prompt as simple string
            formatted_prompt = self.prompt_template.format(
                context=context_text,
                question=question
            )
            
            logger.debug(
                "Sending request to Gemini",
                prompt_length=len(formatted_prompt),
                question_original=question,
                context_length=len(context_text) if context_text else 0
            )
            
            # Generate response using simple text completion
            human_message = HumanMessage(content=formatted_prompt)
            
            response = await self.llm.ainvoke([human_message])
            
            # Extract and log response
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.debug(
                "Received Gemini response",
                response_length=len(response_text),
                response_type=type(response).__name__
            )
            
            # Extract source articles
            source_articles = [
                doc.metadata.get("url", doc.metadata.get("title", f"Document {doc.id}"))
                for doc in context_documents
                if doc.metadata.get("similarity_score", 0) > 0.7
            ]
            
            # Calculate confidence based on context relevance
            confidence = self._calculate_confidence(context_documents, question)
            
            ai_response = AIResponse(
                content=response.content,
                source_articles=source_articles,
                confidence=confidence
            )
            
            logger.info(
                "Successfully generated AI response",
                response_length=len(ai_response.content),
                source_count=len(source_articles),
                confidence=confidence
            )
            
            return ai_response
            
        except Exception as e:
            logger.error(
                "Failed to generate AI response",
                question=question,
                error=str(e),
                exc_info=True
            )
            
            # Return a fallback response
            return AIResponse(
                content="I'm sorry, I'm having trouble processing your question right now. Please try again in a moment.",
                source_articles=[],
                confidence=0.0
            )

    def _format_context(self, documents: List[VectorDocument]) -> str:
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
            context_part += f"\nContent: {doc.content[:500]}...\n"
            
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)

    def _calculate_confidence(self, documents: List[VectorDocument], question: str) -> float:
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