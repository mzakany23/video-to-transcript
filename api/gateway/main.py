"""
API Gateway for Transcription Platform

This gateway provides:
- Health checks for all services
- Reverse proxy routing
- Service discovery
- Load balancing
"""

from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import asyncio
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Transcription Platform Gateway",
    description="""
    API Gateway for the modular transcription platform.
    
    Provides unified access to:
    - Transcription API (job management, processing)
    - Webhook API (webhook handling, cursors, tracking)
    - Orchestration API (batch operations, runners)
    """,
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

# Service configuration
SERVICES = {
    "transcription": {
        "name": "Transcription API",
        "url": "http://localhost:8001",
        "health_path": "/health",
        "prefix": "/api/v1/transcription"
    },
    "webhook": {
        "name": "Webhook API", 
        "url": "http://localhost:8002",
        "health_path": "/health",
        "prefix": "/api/v1/webhook"
    },
    "orchestration": {
        "name": "Orchestration API",
        "url": "http://localhost:8003", 
        "health_path": "/health",
        "prefix": "/api/v1/orchestration"
    }
}

class ServiceHealth:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=5.0)
        
    async def check_service(self, service_name: str, service_config: Dict) -> Dict[str, Any]:
        """Check health of a single service"""
        try:
            url = f"{service_config['url']}{service_config['health_path']}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": service_config["name"],
                    "status": "healthy",
                    "url": service_config["url"],
                    "response_time": response.elapsed.total_seconds(),
                    "version": data.get("version", "unknown"),
                    "last_check": datetime.now().isoformat()
                }
            else:
                return {
                    "name": service_config["name"],
                    "status": "unhealthy",
                    "url": service_config["url"],
                    "error": f"HTTP {response.status_code}",
                    "last_check": datetime.now().isoformat()
                }
                
        except httpx.TimeoutException:
            return {
                "name": service_config["name"],
                "status": "timeout",
                "url": service_config["url"],
                "error": "Request timeout",
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "name": service_config["name"], 
                "status": "error",
                "url": service_config["url"],
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
    
    async def check_all_services(self) -> Dict[str, Any]:
        """Check health of all services"""
        tasks = [
            self.check_service(name, config) 
            for name, config in SERVICES.items()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Determine overall health
        healthy_count = sum(1 for result in results if result["status"] == "healthy")
        total_count = len(results)
        
        overall_status = "healthy" if healthy_count == total_count else (
            "degraded" if healthy_count > 0 else "unhealthy"
        )
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "services": {
                result["name"].lower().replace(" api", ""): result 
                for result in results
            },
            "summary": {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "unhealthy_services": total_count - healthy_count
            }
        }

# Initialize health checker
health_checker = ServiceHealth()

@app.get("/")
async def root():
    """Gateway information"""
    return {
        "name": "Transcription Platform Gateway",
        "version": "1.0.0",
        "description": "API Gateway for modular transcription platform",
        "services": {
            name: {
                "name": config["name"],
                "prefix": config["prefix"]
            }
            for name, config in SERVICES.items()
        },
        "endpoints": {
            "health": "/health",
            "status": "/status", 
            "services": "/services"
        }
    }

@app.get("/health")
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "gateway": "operational"
    }

@app.get("/status")
async def detailed_status():
    """Detailed status including all services"""
    return await health_checker.check_all_services()

@app.get("/services")
async def list_services():
    """List all available services"""
    return {
        "services": {
            name: {
                "name": config["name"],
                "url": config["url"],
                "prefix": config["prefix"],
                "health_endpoint": f"{config['url']}{config['health_path']}"
            }
            for name, config in SERVICES.items()
        }
    }

@app.get("/services/{service_name}/health")
async def service_health(service_name: str):
    """Check health of specific service"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    service_config = SERVICES[service_name]
    result = await health_checker.check_service(service_name, service_config)
    
    return result

# Proxy endpoints for each service
@app.api_route(
    "/api/v1/transcription/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_transcription(request: Request, path: str):
    """Proxy requests to transcription service"""
    return await proxy_request(request, "transcription", path)

@app.api_route(
    "/api/v1/webhook/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"] 
)
async def proxy_webhook(request: Request, path: str):
    """Proxy requests to webhook service"""
    return await proxy_request(request, "webhook", path)

@app.api_route(
    "/api/v1/orchestration/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_orchestration(request: Request, path: str):
    """Proxy requests to orchestration service"""
    return await proxy_request(request, "orchestration", path)

async def proxy_request(request: Request, service_name: str, path: str):
    """Generic request proxy"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    
    service_config = SERVICES[service_name]
    target_url = f"{service_config['url']}/{path}"
    
    # Get query parameters
    query_params = str(request.url.query)
    if query_params:
        target_url += f"?{query_params}"
    
    try:
        # Get request body if present
        body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
        
        # Forward headers (excluding hop-by-hop headers)
        headers = {
            key: value for key, value in request.headers.items()
            if key.lower() not in ["host", "connection", "content-length"]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body
            )
            
            # Return response
            return JSONResponse(
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Gateway timeout - {service_config['name']} did not respond"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503, 
            detail=f"Service unavailable - {service_config['name']} is not reachable"
        )
    except Exception as e:
        logger.error(f"Proxy error for {service_name}: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Bad gateway - Error proxying to {service_config['name']}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)