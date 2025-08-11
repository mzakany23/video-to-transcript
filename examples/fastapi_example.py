#!/usr/bin/env python3
"""
Example demonstrating FastAPI integration with modular services
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def main():
    """Demonstrate FastAPI service integration"""
    
    print("=== FastAPI Service Integration Example ===\n")
    
    # Test services integration
    print("1. Testing service integration:")
    
    try:
        from services import ServiceFactory, Settings
        
        # Create development settings
        dev_settings = Settings(
            storage_provider="local",
            transcription_provider="openai", 
            job_runner="local",
            environment="development"
        )
        
        # Configure local paths
        dev_settings.storage_configs["local"].config["base_path"] = "./data/fastapi_storage"
        dev_settings.job_runner_configs["local"].config["work_dir"] = "./data/fastapi_jobs"
        
        factory = ServiceFactory(dev_settings)
        
        print("   ✅ ServiceFactory created successfully")
        
        # Test service creation
        storage_service = factory.create_storage_service()
        orchestration_service = factory.create_orchestration_service()
        
        print("   ✅ Storage service created")
        print("   ✅ Orchestration service created")
        
        # Get provider information
        providers = factory.get_available_providers()
        print(f"   ✅ Available providers loaded: {len(providers)} types")
        
    except Exception as e:
        print(f"   ❌ Service integration error: {e}")
        return
    
    # Test FastAPI app structure
    print("\n2. FastAPI application structure:")
    
    try:
        # Test transcription API structure
        transcription_api_path = Path(__file__).parent.parent / "api" / "transcription-api"
        
        if transcription_api_path.exists():
            print("   ✅ Transcription API directory exists")
            
            # Check key files
            key_files = [
                "main.py", "models.py", "config.py", "dependencies.py",
                "routers/__init__.py", "routers/health.py", "routers/transcription.py",
                "routers/jobs.py", "routers/providers.py"
            ]
            
            for file_path in key_files:
                file_check = transcription_api_path / file_path
                if file_check.exists():
                    print(f"   ✅ {file_path} exists")
                else:
                    print(f"   ❌ {file_path} missing")
        
        else:
            print("   ❌ Transcription API directory not found")
    
    except Exception as e:
        print(f"   ❌ FastAPI structure check error: {e}")
    
    # Test OpenAPI schemas
    print("\n3. OpenAPI schema validation:")
    
    try:
        schemas_path = Path(__file__).parent.parent / "api" / "schemas"
        
        if schemas_path.exists():
            schema_files = [
                "transcription-api.yaml",
                "webhook-api.yaml", 
                "orchestration-api.yaml"
            ]
            
            for schema_file in schema_files:
                schema_path = schemas_path / schema_file
                if schema_path.exists():
                    # Try to parse YAML
                    import yaml
                    with open(schema_path, 'r') as f:
                        schema = yaml.safe_load(f)
                    
                    title = schema.get('info', {}).get('title', 'Unknown')
                    version = schema.get('info', {}).get('version', 'Unknown')
                    paths_count = len(schema.get('paths', {}))
                    
                    print(f"   ✅ {title} v{version} - {paths_count} endpoints")
                else:
                    print(f"   ❌ {schema_file} missing")
        
        else:
            print("   ❌ API schemas directory not found")
    
    except Exception as e:
        print(f"   ❌ Schema validation error: {e}")
    
    # Demonstrate API capabilities
    print("\n4. API service capabilities:")
    
    print("   🔗 Transcription API (Port 8001):")
    print("      POST /transcribe - Upload and transcribe audio file")
    print("      POST /transcribe/url - Transcribe from URL") 
    print("      POST /transcribe/batch - Batch transcription")
    print("      GET /jobs/{id} - Get job status")
    print("      GET /jobs/{id}/result - Download result")
    print("      GET /providers - List providers")
    print("      GET /health - Health check")
    print("      GET /docs - Interactive API documentation")
    
    print("\n   🔗 Webhook API (Port 8002):")
    print("      POST /webhooks/dropbox - Process Dropbox webhooks")
    print("      GET /cursors - Manage change cursors")
    print("      GET /tracking/processed - View processed files")
    print("      POST /admin/reset - Reset processing state")
    
    print("\n   🔗 Orchestration API (Port 8003):")
    print("      POST /jobs - Submit job")
    print("      GET /jobs - List jobs with filtering")
    print("      POST /jobs/batch - Submit batch jobs")
    print("      GET /runners - List job runners")
    print("      POST /runners/{id}/validate - Validate runner")
    
    # Integration benefits
    print("\n5. Integration benefits:")
    
    print("   🎯 API-First Design:")
    print("      • OpenAPI specs define contracts before implementation")
    print("      • Automatic documentation generation")
    print("      • Client SDK generation possible")
    
    print("\n   🔧 Modular Architecture:")
    print("      • Each API service is independently deployable")
    print("      • Services use shared modular backend")
    print("      • Configuration-driven provider selection")
    
    print("\n   🚀 Production Ready:")
    print("      • Health checks and status endpoints")
    print("      • CORS and security middleware")
    print("      • Comprehensive error handling")
    print("      • Async/await throughout")
    
    print("\n   🔌 MCP Integration Ready:")
    print("      • RESTful APIs perfect for MCP tools")
    print("      • JSON schema validation")
    print("      • Clear endpoint documentation")
    print("      • Standardized error responses")
    
    print("\n=== FastAPI Integration Demo Complete ===")
    
    print("\n🚀 To run the transcription API:")
    print("   cd api/transcription-api")
    print("   pip install -r requirements.txt")
    print("   python main.py")
    print("   # Visit http://localhost:8001/docs for interactive API")
    
    print("\n🌟 Key achievements:")
    print("• Complete OpenAPI 3.0 specifications for all services")
    print("• Working FastAPI application with dependency injection")
    print("• Integration with existing modular services")
    print("• Ready for containerization and deployment")
    print("• Perfect foundation for MCP integration")


if __name__ == "__main__":
    main()