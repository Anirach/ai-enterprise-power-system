"""
AI Power System - Admin Router
System administration and monitoring
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
import os
import redis
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Configuration from environment
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Redis keys
ACTIVE_MODEL_KEY = "ai_power:active_model"
PULLING_MODEL_KEY = "ai_power:pulling_model"
PULL_PROGRESS_KEY = "ai_power:pull_progress"
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:3b")

# Redis client (lazy initialized)
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client

def get_active_model() -> str:
    """Get the currently active model from Redis"""
    try:
        r = get_redis()
        model = r.get(ACTIVE_MODEL_KEY)
        return model if model else DEFAULT_MODEL
    except:
        return DEFAULT_MODEL

def set_active_model(model: str) -> bool:
    """Set the active model in Redis"""
    try:
        r = get_redis()
        r.set(ACTIVE_MODEL_KEY, model)
        return True
    except Exception as e:
        logger.error(f"Failed to set active model: {e}")
        return False


def get_pull_status() -> Optional[Dict[str, Any]]:
    """Get the current pull status from Redis"""
    try:
        r = get_redis()
        model = r.get(PULLING_MODEL_KEY)
        if not model:
            return None
        progress_data = r.get(PULL_PROGRESS_KEY)
        if progress_data:
            return json.loads(progress_data)
        return {"model": model, "status": "pulling", "progress": 0}
    except:
        return None


def set_pull_status(model: str, status: str, progress: int, details: str = ""):
    """Update pull status in Redis"""
    try:
        r = get_redis()
        r.set(PULLING_MODEL_KEY, model)
        r.set(PULL_PROGRESS_KEY, json.dumps({
            "model": model,
            "status": status,
            "progress": progress,
            "details": details
        }))
        # Auto-expire after 30 minutes
        r.expire(PULLING_MODEL_KEY, 1800)
        r.expire(PULL_PROGRESS_KEY, 1800)
    except Exception as e:
        logger.error(f"Failed to set pull status: {e}")


def clear_pull_status():
    """Clear pull status from Redis"""
    try:
        r = get_redis()
        r.delete(PULLING_MODEL_KEY)
        r.delete(PULL_PROGRESS_KEY)
    except:
        pass


class ModelInfo(BaseModel):
    name: str
    size: int
    modified_at: str
    digest: str
    is_active: bool = False


class PullModelRequest(BaseModel):
    model: str


class SetActiveModelRequest(BaseModel):
    model: str


class ServiceStatus(BaseModel):
    name: str
    status: str
    details: Dict[str, Any] = {}


# Service check functions will be injected
check_functions: Dict[str, Any] = {}


def set_check_functions(funcs: Dict[str, Any]):
    global check_functions
    check_functions = funcs


@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List all available Ollama models with active status"""
    try:
        active_model = get_active_model()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            return [
                ModelInfo(
                    name=m["name"],
                    size=m.get("size", 0),
                    modified_at=m.get("modified_at", ""),
                    digest=m.get("digest", ""),
                    is_active=(m["name"] == active_model)
                )
                for m in data.get("models", [])
            ]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {e}")


@router.get("/models/active")
async def get_active_model_endpoint():
    """Get the currently active model"""
    return {"model": get_active_model()}


@router.post("/models/active")
async def set_active_model_endpoint(request: SetActiveModelRequest):
    """Set the active model for chat generation"""
    # Verify model exists
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            model_names = [m["name"] for m in data.get("models", [])]
            
            if request.model not in model_names:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Model '{request.model}' not found. Available: {model_names}"
                )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {e}")
    
    # Set active model
    if set_active_model(request.model):
        logger.info(f"Active model changed to: {request.model}")
        return {"status": "success", "model": request.model}
    else:
        raise HTTPException(status_code=500, detail="Failed to update active model")


async def _stream_pull_progress(model: str) -> AsyncGenerator[str, None]:
    """Stream model pull progress as Server-Sent Events"""
    set_pull_status(model, "starting", 0, "Initializing download...")
    
    try:
        async with httpx.AsyncClient(timeout=1800.0) as client:
            async with client.stream(
                "POST",
                f"{ollama_base_url}/api/pull",
                json={"name": model, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            # Calculate progress percentage
                            progress = 0
                            status = data.get("status", "")
                            details = status
                            
                            if "completed" in data and "total" in data:
                                total = data["total"]
                                completed = data["completed"]
                                if total > 0:
                                    progress = int((completed / total) * 100)
                                    completedMB = completed / 1024 / 1024
                                    totalMB = total / 1024 / 1024
                                    details = f"{status}: {completedMB:.1f} MB / {totalMB:.1f} MB"
                            
                            # Update Redis with current progress
                            set_pull_status(model, status, progress, details)
                            
                            # Format the message
                            message = {
                                "model": model,
                                "status": status,
                                "progress": progress,
                                "completed": data.get("completed", 0),
                                "total": data.get("total", 0),
                                "details": details,
                                "digest": data.get("digest", "")
                            }
                            
                            yield f"data: {json.dumps(message)}\n\n"
                            
                        except json.JSONDecodeError:
                            continue
                
                # Send completion message and clear status
                clear_pull_status()
                yield f"data: {json.dumps({'status': 'success', 'progress': 100, 'model': model, 'message': 'Model pulled successfully'})}\n\n"
                
    except Exception as e:
        logger.error(f"Pull stream error: {e}")
        clear_pull_status()
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"


@router.get("/models/pull/status")
async def get_pull_status_endpoint():
    """Get the current model pull status"""
    status = get_pull_status()
    if status:
        return {"pulling": True, **status}
    return {"pulling": False}


@router.get("/models/pull/{model_name}/stream")
async def pull_model_stream(model_name: str):
    """Pull a model with streaming progress updates (SSE)"""
    # Check if already pulling this model
    current_status = get_pull_status()
    if current_status and current_status.get("model") == model_name:
        # Already pulling, just stream current status
        pass
    
    return StreamingResponse(
        _stream_pull_progress(model_name),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/models/pull")
async def pull_model(request: PullModelRequest):
    """Pull a new Ollama model (non-streaming, returns when complete)"""
    try:
        async with httpx.AsyncClient(timeout=1800.0) as client:  # 30 min timeout for large models
            response = await client.post(
                f"{ollama_base_url}/api/pull",
                json={"name": request.model, "stream": False}
            )
            response.raise_for_status()
            return {"status": "success", "model": request.model}
    except httpx.TimeoutException:
        return {"status": "pulling", "message": "Model is being pulled. This may take several minutes."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete an Ollama model"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{ollama_base_url}/api/delete",
                json={"name": model_name}
            )
            if response.status_code == 200:
                return {"status": "deleted", "model": model_name}
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to delete model")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services", response_model=List[ServiceStatus])
async def check_services():
    """Check status of all services"""
    services = []
    
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                services.append(ServiceStatus(
                    name="ollama",
                    status="healthy",
                    details={"models_count": len(models)}
                ))
            else:
                services.append(ServiceStatus(name="ollama", status="unhealthy"))
    except:
        services.append(ServiceStatus(name="ollama", status="unreachable"))
    
    # Check n8n
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://n8n:5678/healthz")
            if response.status_code == 200:
                services.append(ServiceStatus(
                    name="n8n",
                    status="healthy",
                    details={"url": "http://localhost:5678"}
                ))
            else:
                services.append(ServiceStatus(name="n8n", status="unhealthy"))
    except:
        services.append(ServiceStatus(name="n8n", status="unreachable"))
    
    # Check other services using injected functions
    for service_name, check_func in check_functions.items():
        try:
            result = await check_func()
            services.append(ServiceStatus(
                name=service_name,
                status="healthy" if result.get("healthy") else "unhealthy",
                details=result.get("details", {})
            ))
        except Exception as e:
            services.append(ServiceStatus(
                name=service_name,
                status="error",
                details={"error": str(e)}
            ))
    
    return services


@router.get("/system-info")
async def get_system_info():
    """Get system information"""
    import platform
    import psutil
    
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": round(disk.used / disk.total * 100, 1)
            }
        }
    except ImportError:
        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "note": "Install psutil for detailed system info"
        }


@router.get("/links")
async def get_service_links():
    """Get quick links to all services"""
    return {
        "services": [
            {"name": "API Documentation", "url": "/docs", "description": "Swagger UI"},
            {"name": "n8n Automation", "url": "http://localhost:5678", "description": "Workflow automation"},
            {"name": "Qdrant Dashboard", "url": "http://localhost:6333/dashboard", "description": "Vector DB UI"},
            {"name": "PostgreSQL", "url": "postgresql://localhost:5432", "description": "Database (use client)"},
            {"name": "Redis", "url": "redis://localhost:6379", "description": "Cache (use client)"}
        ]
    }


