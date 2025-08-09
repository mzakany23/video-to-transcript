"""
Providers router for Transcription API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from ..models import ProviderInfo
from ..dependencies import get_service_factory

router = APIRouter()


@router.get("/", response_model=List[ProviderInfo])
async def list_providers(factory = Depends(get_service_factory)):
    """
    List available transcription providers
    
    Get information about all available transcription and storage providers
    """
    try:
        providers_info = factory.get_available_providers()
        
        provider_list = []
        
        # Add transcription providers
        for provider_name in providers_info.get("transcription", {}).get("available", []):
            enabled = provider_name in providers_info.get("transcription", {}).get("enabled", [])
            
            provider_info = ProviderInfo(
                id=provider_name,
                name=provider_name.title(),
                description=f"{provider_name.title()} transcription provider",
                enabled=enabled,
                available=True,  # TODO: Check actual availability
                supported_formats=[".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac"],
                configuration={}  # Don't expose sensitive config
            )
            provider_list.append(provider_info)
        
        # Add storage providers  
        for provider_name in providers_info.get("storage", {}).get("available", []):
            enabled = provider_name in providers_info.get("storage", {}).get("enabled", [])
            
            provider_info = ProviderInfo(
                id=f"storage_{provider_name}",
                name=f"{provider_name.title()} Storage",
                description=f"{provider_name.title()} storage provider",
                enabled=enabled,
                available=True,  # TODO: Check actual availability
                supported_formats=["*"],
                configuration={}
            )
            provider_list.append(provider_info)
        
        return provider_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list providers: {str(e)}"
        )


@router.post("/{provider_id}/validate")
async def validate_provider(
    provider_id: str,
    factory = Depends(get_service_factory)
) -> Dict[str, Any]:
    """
    Validate provider configuration
    
    Test if a specific provider is properly configured and accessible
    """
    try:
        # Get configuration validation
        validation = factory.validate_configuration()
        
        # Find provider in validation results
        provider_status = None
        for provider_type, providers in validation.get("provider_status", {}).items():
            if provider_id == providers.get("name") or provider_id.endswith(providers.get("name", "")):
                provider_status = providers
                break
        
        if not provider_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider {provider_id} not found"
            )
        
        return {
            "provider_id": provider_id,
            "valid": provider_status.get("status") == "valid",
            "message": provider_status.get("error", "Provider is valid and available"),
            "details": {
                "status": provider_status.get("status"),
                "name": provider_status.get("name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate provider: {str(e)}"
        )