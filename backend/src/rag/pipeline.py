"""
AI Power System - RAG Pipeline
Combines retrieval and generation for question answering
With document awareness for knowledge base queries
"""
import httpx
import re
import redis
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from .embeddings import EmbeddingService
from .retriever import VectorRetriever

logger = logging.getLogger(__name__)

# Redis config for active model
ACTIVE_MODEL_KEY = "ai_power:active_model"

def _get_active_model_from_redis() -> Optional[str]:
    """Get the currently active model from Redis"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        return r.get(ACTIVE_MODEL_KEY)
    except:
        return None

# Keywords that indicate a document list query
DOCUMENT_QUERY_PATTERNS = [
    r"what\s+(documents?|files?)\s+(do\s+you\s+have|are\s+there|exist)",
    r"list\s+(all\s+)?(documents?|files?)",
    r"show\s+(me\s+)?(all\s+)?(documents?|files?)",
    r"(documents?|files?)\s+(in\s+)?(the\s+)?(knowledge\s+base|system)",
    r"how\s+many\s+(documents?|files?)",
    r"(มี|แสดง|รายการ).*(เอกสาร|ไฟล์)",
    r"เอกสาร.*(มี|อะไรบ้าง|ทั้งหมด)",
]


def is_document_query(text: str) -> bool:
    """Check if the query is asking about documents in the knowledge base"""
    text_lower = text.lower()
    for pattern in DOCUMENT_QUERY_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


class RAGPipeline:
    """Complete RAG pipeline: embed query -> retrieve -> generate"""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        retriever: VectorRetriever,
        ollama_base_url: str,
        default_model: str = "llama3.2:3b",
        db_service=None
    ):
        self.embedding_service = embedding_service
        self.retriever = retriever
        self.ollama_base_url = ollama_base_url
        self.default_model = default_model
        self.db_service = db_service
    
    async def _get_document_list_context(self) -> str:
        """Get formatted document list for context"""
        if not self.db_service:
            return ""
        
        try:
            summary = await self.db_service.get_documents_summary()
            docs = await self.db_service.get_document_names()
            
            if not docs:
                return "The knowledge base is currently empty. No documents have been uploaded yet."
            
            # Format document list
            doc_lines = []
            for i, doc in enumerate(docs, 1):
                name = doc.get("name", "Unknown")
                file_type = doc.get("file_type", "")
                pages = doc.get("page_count", 0)
                words = doc.get("word_count", 0)
                
                doc_info = f"{i}. {name}"
                if pages > 0:
                    doc_info += f" ({pages} pages)"
                if words > 0:
                    doc_info += f" - {words:,} words"
                doc_lines.append(doc_info)
            
            total = summary.get("total", len(docs))
            completed = summary.get("completed", len(docs))
            total_words = summary.get("total_words", 0)
            
            context = f"""KNOWLEDGE BASE INFORMATION:
Total Documents: {total}
Processed Documents: {completed}
Total Words: {total_words:,}

Document List:
{chr(10).join(doc_lines)}
"""
            return context
            
        except Exception as e:
            logger.error(f"Failed to get document list: {e}")
            return ""
    
    def _get_model(self, model: Optional[str] = None) -> str:
        """Get the model to use - checks Redis for active model first"""
        if model:
            return model
        # Try to get active model from Redis
        active = _get_active_model_from_redis()
        if active:
            return active
        return self.default_model
    
    async def query(
        self,
        question: str,
        top_k: int = 5,
        model: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute RAG query: retrieve context and generate answer"""
        model = self._get_model(model)
        
        # Step 1: Embed the question
        query_embedding = await self.embedding_service.embed_text(question)
        
        # Step 2: Retrieve relevant documents
        retrieved_docs = await self.retriever.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_dict=filter_dict
        )
        
        # Step 3: Build context from retrieved documents
        context = self._build_context(retrieved_docs)
        
        # Step 4: Generate answer using LLM
        answer = await self._generate_answer(question, context, model)
        
        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "text": doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"],
                    "score": doc["score"],
                    "metadata": doc["metadata"]
                }
                for doc in retrieved_docs
            ],
            "model": model
        }
    
    async def query_stream(
        self,
        question: str,
        top_k: int = 5,
        model: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Execute RAG query with streaming response"""
        model = self._get_model(model)
        
        # Retrieve context
        query_embedding = await self.embedding_service.embed_text(question)
        retrieved_docs = await self.retriever.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_dict=filter_dict
        )
        context = self._build_context(retrieved_docs)
        
        # Stream the response
        async for chunk in self._generate_answer_stream(question, context, model):
            yield chunk
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents"""
        if not documents:
            return "No relevant context found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"[Document {i}]\n{doc['text']}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_answer(
        self,
        question: str,
        context: str,
        model: str
    ) -> str:
        """Generate answer using Ollama"""
        prompt = self._build_prompt(question, context)
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min for reasoning models
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise
    
    async def _generate_answer_stream(
        self,
        question: str,
        context: str,
        model: str
    ) -> AsyncGenerator[str, None]:
        """Generate answer with streaming"""
        prompt = self._build_prompt(question, context)
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min for reasoning models
                async with client.stream(
                    "POST",
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"Error: {str(e)}"
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build the prompt for the LLM"""
        return f"""You are a helpful AI assistant. Answer the question based on the provided context.
If the context doesn't contain relevant information, say so and provide a general answer.

Context:
{context}

Question: {question}

Answer:"""
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        use_rag: bool = True,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Chat with optional RAG enhancement and document awareness"""
        model = self._get_model(model)
        
        # Get the last user message for RAG
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        # Check if this is a document query
        document_context = ""
        if last_user_msg and is_document_query(last_user_msg):
            document_context = await self._get_document_list_context()
        
        # If RAG is enabled and we have a user message, enhance with context
        rag_context = ""
        sources = []
        if use_rag and last_user_msg and not document_context:
            # Only do RAG retrieval if not a document list query
            query_embedding = await self.embedding_service.embed_text(last_user_msg)
            retrieved_docs = await self.retriever.search(
                query_embedding=query_embedding,
                top_k=3
            )
            if retrieved_docs:
                rag_context = self._build_context(retrieved_docs)
                sources = [
                    {
                        "text": doc["text"][:200],
                        "score": doc["score"],
                        "metadata": doc.get("metadata", {})
                    }
                    for doc in retrieved_docs
                ]
        
        # Build system message with context
        system_msg = """You are a helpful AI assistant for the AI Power System.
You have access to a knowledge base of documents.
When asked about documents in the knowledge base, provide accurate information based on the context.
Always be helpful, accurate, and concise."""
        
        if document_context:
            system_msg += f"\n\n{document_context}"
        elif rag_context:
            system_msg += f"\n\nRelevant context from knowledge base:\n{rag_context}"
        
        # Call Ollama chat API
        try:
            chat_messages = [{"role": "system", "content": system_msg}] + messages
            
            logger.info(f"Calling Ollama chat with model: {model}")
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min for reasoning models
                response = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": chat_messages,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "message": data.get("message", {}).get("content", ""),
                    "sources": sources,
                    "model": model
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Chat HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Chat request error: {type(e).__name__} - {e}")
            raise
        except Exception as e:
            logger.error(f"Chat failed: {type(e).__name__} - {e}")
            raise
