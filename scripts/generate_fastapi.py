#!/usr/bin/env python3
"""
Generate FastAPI application stubs from OpenAPI YAML specifications
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, List


class FastAPIGenerator:
    """Generate FastAPI applications from OpenAPI specs"""
    
    def __init__(self, spec_file: str, output_dir: str):
        self.spec_file = Path(spec_file)
        self.output_dir = Path(output_dir)
        self.spec = self._load_spec()
        self.service_name = self._extract_service_name()
    
    def _load_spec(self) -> Dict[str, Any]:
        """Load OpenAPI specification"""
        with open(self.spec_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _extract_service_name(self) -> str:
        """Extract service name from spec"""
        return self.spec['info']['title'].lower().replace(' ', '_').replace('-', '_')
    
    def generate(self):
        """Generate complete FastAPI application"""
        print(f"🔧 Generating FastAPI app for {self.spec['info']['title']}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate files
        self._generate_main()
        self._generate_models()
        self._generate_routers()
        self._generate_dependencies()
        self._generate_config()
        self._generate_dockerfile()
        self._generate_requirements()
        
        print(f"✅ FastAPI application generated in {self.output_dir}")
    
    def _generate_main(self):
        """Generate main FastAPI application"""
        main_content = f'''"""
{self.spec['info']['title']} FastAPI Application
Generated from OpenAPI specification

{self.spec['info']['description']}
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routers import {self._get_router_imports()}
from .config import get_settings
from .dependencies import get_service_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"🚀 Starting {{get_settings().service_name}}")
    
    # Initialize services
    factory = get_service_factory()
    validation = factory.validate_configuration()
    
    if not validation["valid"]:
        print("❌ Configuration validation failed:")
        for error in validation["errors"]:
            print(f"  - {{error}}")
        raise RuntimeError("Invalid service configuration")
    
    print("✅ Service initialized successfully")
    
    yield
    
    # Shutdown
    print(f"🛑 Shutting down {{get_settings().service_name}}")


# Create FastAPI application
app = FastAPI(
    title="{self.spec['info']['title']}",
    description="{self.spec['info']['description']}",
    version="{self.spec['info']['version']}",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{self._generate_router_includes()}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={{
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "timestamp": "{{__import__('datetime').datetime.now().isoformat()}}"
        }}
    )


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
'''
        
        with open(self.output_dir / "main.py", "w") as f:
            f.write(main_content)
    
    def _get_router_imports(self) -> str:
        """Get router import statements"""
        tags = [tag['name'] for tag in self.spec.get('tags', [])]
        return ", ".join([f"{tag}_router" for tag in tags if tag not in ['health']])
    
    def _generate_router_includes(self) -> str:
        """Generate router include statements"""
        tags = [tag['name'] for tag in self.spec.get('tags', [])]
        includes = []
        
        for tag in tags:
            if tag == 'health':
                includes.append(f'app.include_router(health_router, tags=["health"])')
            else:
                includes.append(f'app.include_router({tag}_router, prefix="/{tag}", tags=["{tag}"])')
        
        return "\\n".join(includes)
    
    def _generate_models(self):
        """Generate Pydantic models from schemas"""
        models_content = f'''"""
Pydantic models for {self.spec['info']['title']}
Generated from OpenAPI specification
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


# Enums
{self._generate_enums()}

# Models
{self._generate_model_classes()}
'''
        
        with open(self.output_dir / "models.py", "w") as f:
            f.write(models_content)
    
    def _generate_enums(self) -> str:
        """Generate enum classes"""
        enums = []
        schemas = self.spec.get('components', {}).get('schemas', {})
        
        for name, schema in schemas.items():
            if schema.get('type') == 'string' and 'enum' in schema:
                enum_values = []
                for value in schema['enum']:
                    enum_values.append(f'    {value.upper()} = "{value}"')
                
                enum_class = f'''
class {name}(str, Enum):
    """Enum for {name}"""
{chr(10).join(enum_values)}
'''
                enums.append(enum_class)
        
        return "\\n".join(enums)
    
    def _generate_model_classes(self) -> str:
        """Generate Pydantic model classes"""
        models = []
        schemas = self.spec.get('components', {}).get('schemas', {})
        
        for name, schema in schemas.items():
            if schema.get('type') == 'object':
                fields = []
                
                properties = schema.get('properties', {})
                required = schema.get('required', [])
                
                for field_name, field_schema in properties.items():
                    field_type = self._get_python_type(field_schema)
                    field_optional = field_name not in required
                    default_value = field_schema.get('default', 'None' if field_optional else '...')
                    description = field_schema.get('description', '')
                    
                    if field_optional and default_value == 'None':
                        field_type = f"Optional[{field_type}]"
                    
                    field_def = f'    {field_name}: {field_type}'
                    if default_value != '...':
                        field_def += f' = {default_value}'
                    if description:
                        field_def += f' = Field(description="{description}")'
                    
                    fields.append(field_def)
                
                model_class = f'''
class {name}(BaseModel):
    """Model for {name}"""
{chr(10).join(fields) if fields else "    pass"}
'''
                models.append(model_class)
        
        return "\\n".join(models)
    
    def _get_python_type(self, schema: Dict[str, Any]) -> str:
        """Convert OpenAPI schema type to Python type"""
        schema_type = schema.get('type', 'any')
        schema_format = schema.get('format')
        
        if '$ref' in schema:
            return schema['$ref'].split('/')[-1]
        
        type_mapping = {
            'string': 'str',
            'integer': 'int',
            'number': 'float',
            'boolean': 'bool',
            'array': f"List[{self._get_python_type(schema.get('items', {}))}]",
            'object': 'Dict[str, Any]'
        }
        
        if schema_format == 'date-time':
            return 'datetime'
        elif schema_format == 'binary':
            return 'bytes'
        
        return type_mapping.get(schema_type, 'Any')
    
    def _generate_routers(self):
        """Generate FastAPI routers for each tag"""
        tags = [tag['name'] for tag in self.spec.get('tags', [])]
        
        # Create routers directory
        routers_dir = self.output_dir / "routers"
        routers_dir.mkdir(exist_ok=True)
        
        # Generate __init__.py
        init_content = f'''"""
Routers for {self.spec['info']['title']}
"""

{chr(10).join([f"from .{tag} import router as {tag}_router" for tag in tags])}

__all__ = [
{chr(10).join([f'    "{tag}_router",' for tag in tags])}
]
'''
        with open(routers_dir / "__init__.py", "w") as f:
            f.write(init_content)
        
        # Generate individual router files
        for tag in tags:
            self._generate_router_file(tag, routers_dir)
    
    def _generate_router_file(self, tag: str, routers_dir: Path):
        """Generate individual router file"""
        router_content = f'''"""
{tag.title()} router for {self.spec['info']['title']}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from ..models import *
from ..dependencies import get_service_factory

router = APIRouter()

# TODO: Implement endpoints for {tag}
{self._generate_router_endpoints(tag)}
'''
        
        with open(routers_dir / f"{tag}.py", "w") as f:
            f.write(router_content)
    
    def _generate_router_endpoints(self, tag: str) -> str:
        """Generate router endpoints for a tag"""
        endpoints = []
        paths = self.spec.get('paths', {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                
                operation_tags = operation.get('tags', [])
                if tag not in operation_tags:
                    continue
                
                operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")
                summary = operation.get('summary', '')
                
                endpoint = f'''
@router.{method.lower()}("{path}")
async def {operation_id}():
    """
    {summary}
    
    TODO: Implement this endpoint
    """
    raise HTTPException(
        status_code=501,
        detail="Endpoint not implemented yet"
    )
'''
                endpoints.append(endpoint)
        
        return "\\n".join(endpoints)
    
    def _generate_dependencies(self):
        """Generate dependency injection"""
        deps_content = f'''"""
Dependency injection for {self.spec['info']['title']}
"""

import os
import sys
from pathlib import Path
from functools import lru_cache

# Add project root to path for services import
sys.path.append(str(Path(__file__).parent.parent.parent))

from services import ServiceFactory, Settings


@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    return Settings.from_env()


@lru_cache()
def get_service_factory() -> ServiceFactory:
    """Get service factory instance"""
    settings = get_settings()
    return ServiceFactory(settings)


# Service-specific dependencies
def get_{self.service_name}_service():
    """Get {self.service_name} service instance"""
    factory = get_service_factory()
    # TODO: Implement service creation based on service type
    pass
'''
        
        with open(self.output_dir / "dependencies.py", "w") as f:
            f.write(deps_content)
    
    def _generate_config(self):
        """Generate configuration"""
        config_content = f'''"""
Configuration for {self.spec['info']['title']}
"""

import os
from pydantic import BaseSettings


class APISettings(BaseSettings):
    """API configuration settings"""
    
    # Server configuration
    service_name: str = "{self.service_name}"
    host: str = "0.0.0.0"
    port: int = {self._get_default_port()}
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_origins: list = ["*"]
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    # Service-specific configuration
    # TODO: Add service-specific settings
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> APISettings:
    """Get settings instance"""
    return APISettings()
'''
        
        with open(self.output_dir / "config.py", "w") as f:
            f.write(config_content)
    
    def _get_default_port(self) -> int:
        """Get default port based on service type"""
        service_ports = {
            'transcription_api': 8001,
            'webhook_api': 8002,
            'orchestration_api': 8003
        }
        return service_ports.get(self.service_name, 8000)
    
    def _generate_dockerfile(self):
        """Generate Dockerfile"""
        dockerfile_content = f'''# Dockerfile for {self.spec['info']['title']}
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE {self._get_default_port()}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{self._get_default_port()}/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{self._get_default_port()}"]
'''
        
        with open(self.output_dir / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
    
    def _generate_requirements(self):
        """Generate requirements.txt"""
        requirements_content = '''# FastAPI and dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# HTTP client
httpx==0.25.2

# Async support
asyncio==3.4.3

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.12.0
isort==5.13.0
mypy==1.8.0

# Add service-specific requirements here
'''
        
        with open(self.output_dir / "requirements.txt", "w") as f:
            f.write(requirements_content)


def main():
    """Main generator function"""
    if len(sys.argv) != 3:
        print("Usage: python generate_fastapi.py <openapi_spec.yaml> <output_directory>")
        sys.exit(1)
    
    spec_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(spec_file):
        print(f"❌ OpenAPI spec file not found: {spec_file}")
        sys.exit(1)
    
    generator = FastAPIGenerator(spec_file, output_dir)
    generator.generate()
    
    print(f"\\n🎉 FastAPI application generated successfully!")
    print(f"📁 Output directory: {output_dir}")
    print(f"🚀 To run the application:")
    print(f"   cd {output_dir}")
    print(f"   pip install -r requirements.txt")
    print(f"   python main.py")


if __name__ == "__main__":
    main()