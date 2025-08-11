#!/usr/bin/env python3
"""
Example of using the configuration system to create services
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from services import ServiceFactory, Settings


def main():
    """Demonstrate configuration system usage"""
    
    print("=== Transcription Services Configuration Example ===\n")
    
    # Option 1: Use environment-based configuration
    print("1. Environment-based configuration:")
    env_settings = Settings.from_env()
    env_factory = ServiceFactory(env_settings)
    
    print(f"   Storage Provider: {env_settings.storage_provider}")
    print(f"   Transcription Provider: {env_settings.transcription_provider}")
    print(f"   Job Runner: {env_settings.job_runner}")
    print(f"   Environment: {env_settings.environment}")
    
    # Show available providers
    providers = env_factory.get_available_providers()
    print(f"\n   Available Storage Providers: {providers['storage']['available']}")
    print(f"   Available Transcription Providers: {providers['transcription']['available']}")
    print(f"   Available Job Runners: {providers['job_runner']['available']}")
    
    # Option 2: Custom configuration
    print("\n2. Custom configuration for development:")
    dev_settings = Settings(
        storage_provider="local",
        transcription_provider="openai",
        job_runner="local",
        environment="development",
        log_level="DEBUG"
    )
    
    # Configure local storage
    dev_settings.storage_configs["local"].config["base_path"] = "./data/dev_storage"
    
    # Configure local job runner
    dev_settings.job_runner_configs["local"].config["work_dir"] = "./data/dev_jobs"
    
    dev_factory = ServiceFactory(dev_settings)
    
    print(f"   Storage Provider: {dev_settings.storage_provider}")
    print(f"   Job Runner: {dev_settings.job_runner}")
    print(f"   Environment: {dev_settings.environment}")
    
    # Option 3: Create and use services
    print("\n3. Creating services:")
    
    try:
        # Create storage service
        storage_service = dev_factory.create_storage_service()
        print("   ✓ Storage service created successfully")
        
        # Create job runner
        job_runner = dev_factory.create_job_runner() 
        print("   ✓ Job runner created successfully")
        
        # Create orchestration service
        orchestration = dev_factory.create_orchestration_service()
        print("   ✓ Orchestration service created successfully")
        
        # Get runner info
        runner_info = orchestration.get_runner_info()
        print(f"   Runner Type: {runner_info['runner_type']}")
        print(f"   Capabilities: {list(runner_info['capabilities'].keys())}")
        
    except Exception as e:
        print(f"   ✗ Error creating services: {e}")
    
    # Option 4: Validate configuration
    print("\n4. Configuration validation:")
    validation = dev_factory.validate_configuration()
    
    if validation["valid"]:
        print("   ✓ Configuration is valid")
        for provider_type, status in validation["provider_status"].items():
            print(f"   {provider_type}: {status['name']} ({status['status']})")
    else:
        print("   ✗ Configuration has errors:")
        for error in validation["errors"]:
            print(f"     - {error}")
    
    if validation["warnings"]:
        print("   Warnings:")
        for warning in validation["warnings"]:
            print(f"     - {warning}")
    
    # Option 5: Save configuration to file
    print("\n5. Configuration file operations:")
    config_file = "./example_config.json"
    
    try:
        dev_settings.to_file(config_file)
        print(f"   ✓ Configuration saved to {config_file}")
        
        # Load it back
        loaded_settings = Settings.from_file(config_file)
        print(f"   ✓ Configuration loaded from {config_file}")
        print(f"   Loaded storage provider: {loaded_settings.storage_provider}")
        
        # Clean up
        os.unlink(config_file)
        print("   ✓ Configuration file cleaned up")
        
    except Exception as e:
        print(f"   ✗ Error with configuration file: {e}")
    
    # Option 6: Provider switching example
    print("\n6. Dynamic provider switching:")
    
    # Show current provider
    print(f"   Current storage provider: {dev_settings.storage_provider}")
    
    # Switch to different provider if available
    enabled_storage = dev_settings.get_enabled_providers("storage")
    print(f"   Enabled storage providers: {list(enabled_storage.keys())}")
    
    # Try creating different storage providers
    for provider_name in enabled_storage.keys():
        try:
            provider = dev_factory.create_storage_provider(provider_name)
            print(f"   ✓ {provider_name} provider created successfully")
        except Exception as e:
            print(f"   ✗ {provider_name} provider failed: {e}")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()