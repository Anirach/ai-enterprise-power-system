"""
AI Power System - RAG Pipeline
Combines retrieval and generation for question answering
"""
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
import logging

from .embeddings import EmbeddingService
from .retriever import VectorRetriever

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Complete RAG pipeline: embed query -> retrieve -> generate"""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        retriever: VectorRetriever,
        ollama_base_url: str,
        default_model: str = "llama3.2:3b"
    ):
        self.embedding_service = embedding_service
        self.retriever = retriever
        self.ollama_base_url = ollama_base_url
        self.default_model = default_model
    
    async def query(
        self,
        question: str,
        top_k: int = 5,
        model: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute RAG query: retrieve context and generate answer"""
        model = model or self.default_model
        
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
        model = model or self.default_model
        
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
            async with httpx.AsyncClient(timeout=120.0) as client:
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
        """Chat with optional RAG enhancement"""
        model = model or self.default_model
        
        # Get the last user message for RAG
        last_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        
        # If RAG is enabled and we have a user message, enhance with context
        context = ""
        sources = []
        if use_rag and last_user_msg:
            query_embedding = await self.embedding_service.embed_text(last_user_msg)
            retrieved_docs = await self.retriever.search(
                query_embedding=query_embedding,
                top_k=3
            )
            if retrieved_docs:
                context = self._build_context(retrieved_docs)
                sources = [
                    {"text": doc["text"][:200], "score": doc["score"]}
                    for doc in retrieved_docs
                ]
        
        # Build system message with context
        system_msg = "You are a helpful AI assistant."
        if context:
            system_msg += f"\n\nRelevant context:\n{context}"
        
        # Call Ollama chat API
        try:
            chat_messages = [{"role": "system", "content": system_msg}] + messages
            
            async with httpx.AsyncClient(timeout=120.0) as client:
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
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise


