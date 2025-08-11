"""
Cursors router for Webhook API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from ..dependencies import get_cursor_manager

router = APIRouter()


@router.get("/")
async def list_cursors(cursor_manager = Depends(get_cursor_manager)):
    """List all stored cursors"""
    try:
        cursors = await cursor_manager.list_cursors()
        cursor_info = await cursor_manager.get_cursor_info()
        
        return {
            "cursors": cursors,
            "count": len(cursors),
            "last_updated": cursor_info.get("last_updated"),
            "storage_provider": cursor_info.get("storage_provider")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cursors: {str(e)}"
        )


@router.get("/{path:path}")
async def get_cursor(path: str, cursor_manager = Depends(get_cursor_manager)):
    """Get cursor for specific path"""
    try:
        cursor = await cursor_manager.get_cursor(path)
        
        if cursor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cursor not found for path: {path}"
            )
        
        return {
            "path": path,
            "cursor": cursor
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cursor: {str(e)}"
        )


@router.put("/{path:path}")
async def set_cursor(
    path: str,
    cursor_data: Dict[str, str],
    cursor_manager = Depends(get_cursor_manager)
):
    """Set or update cursor for path"""
    try:
        cursor = cursor_data.get("cursor")
        if not cursor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cursor value required"
            )
        
        await cursor_manager.set_cursor(path, cursor)
        
        return {
            "path": path,
            "cursor": cursor,
            "message": "Cursor set successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cursor: {str(e)}"
        )


@router.delete("/")
async def reset_all_cursors(
    confirm_data: Dict[str, bool],
    cursor_manager = Depends(get_cursor_manager)
):
    """Reset all cursors"""
    try:
        if not confirm_data.get("confirm", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required to reset cursors"
            )
        
        await cursor_manager.reset_all_cursors()
        
        return {
            "reset": True,
            "message": "All cursors reset successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset cursors: {str(e)}"
        )