"""
AI Power System - Chat Router
Handles chat and RAG queries
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    use_rag: bool = True
    stream: bool = False


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    model: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    message: str
    sources: List[Dict[str, Any]] = []
    model: str


# These will be injected from main.py
rag_pipeline = None


def set_rag_pipeline(pipeline):
    global rag_pipeline
    rag_pipeline = pipeline


@router.post("/query", response_model=Dict[str, Any])
async def query(request: QueryRequest):
    """Execute a RAG query"""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    try:
        if request.stream:
            async def generate():
                async for chunk in rag_pipeline.query_stream(
                    question=request.question,
                    top_k=request.top_k,
                    model=request.model
                ):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        
        result = await rag_pipeline.query(
            question=request.question,
            top_k=request.top_k,
            model=request.model
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with AI using optional RAG enhancement"""
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        result = await rag_pipeline.chat(
            messages=messages,
            use_rag=request.use_rag,
            model=request.model
        )
        
        return ChatResponse(
            message=result["message"],
            sources=result.get("sources", []),
            model=result["model"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


