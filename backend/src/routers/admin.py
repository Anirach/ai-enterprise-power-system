"""
AI Power System - Admin Router
System administration and monitoring
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import os

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Configuration from environment
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")


class ModelInfo(BaseModel):
    name: str
    size: int
    modified_at: str
    digest: str


class PullModelRequest(BaseModel):
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
    """List all available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            
            return [
                ModelInfo(
                    name=m["name"],
                    size=m.get("size", 0),
                    modified_at=m.get("modified_at", ""),
                    digest=m.get("digest", "")
                )
                for m in data.get("models", [])
            ]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {e}")


@router.post("/models/pull")
async def pull_model(request: PullModelRequest):
    """Pull a new Ollama model"""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 min timeout for large models
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


