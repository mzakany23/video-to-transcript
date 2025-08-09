"""
Webhooks router for Webhook API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from typing import Dict, Any, Optional

from ..dependencies import get_webhook_service

router = APIRouter()


@router.post("/dropbox")
async def process_dropbox_webhook(
    request: Request,
    x_dropbox_signature: Optional[str] = Header(None),
    webhook_service = Depends(get_webhook_service)
):
    """Process Dropbox webhook notifications"""
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Get JSON payload
        payload = await request.json()
        
        # Verify signature (simplified - full implementation would use the handler)
        if not x_dropbox_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Dropbox signature"
            )
        
        # Process the webhook
        result = await webhook_service.process_notification(
            notification_data=payload,
            handler_type="dropbox"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/dropbox")
async def verify_dropbox_webhook(challenge: str):
    """Handle Dropbox webhook verification"""
    # Return the challenge for verification
    return challenge


@router.post("/manual/process")
async def process_manual_webhook(
    payload: Dict[str, Any],
    handler_type: str = "dropbox",
    simulate: bool = False,
    webhook_service = Depends(get_webhook_service)
):
    """Manually trigger webhook processing"""
    try:
        # Add simulation flag to payload
        if simulate:
            payload["_simulate"] = True
        
        result = await webhook_service.process_notification(
            notification_data=payload,
            handler_type=handler_type
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual webhook processing failed: {str(e)}"
        )