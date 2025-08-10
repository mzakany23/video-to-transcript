"""
Authentication utilities
"""

import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """Simple API key authentication"""

    def __init__(self, api_key_name: str = "X-API-Key", auto_error: bool = True):
        self.api_key_name = api_key_name
        self.auto_error = auto_error
        self.api_key_header = APIKeyHeader(name=api_key_name, auto_error=auto_error)

        # Load valid API keys from environment
        self.valid_keys = self._load_api_keys()

        if not self.valid_keys:
            logger.warning("No API keys configured - authentication disabled")

    def _load_api_keys(self) -> dict[str, dict[str, Any]]:
        """Load API keys from environment variables"""
        keys = {}

        # Single API key
        single_key = os.environ.get("API_KEY")
        if single_key:
            keys[single_key] = {
                "name": "default",
                "permissions": ["read", "write"],
                "created_at": datetime.now().isoformat(),
            }

        # Multiple API keys (comma-separated)
        multi_keys = os.environ.get("API_KEYS", "").split(",")
        for i, key in enumerate(multi_keys):
            key = key.strip()
            if key:
                keys[key] = {
                    "name": f"key-{i + 1}",
                    "permissions": ["read", "write"],
                    "created_at": datetime.now().isoformat(),
                }

        return keys

    async def __call__(self, api_key: str = Depends(lambda: None)) -> Optional[dict[str, Any]]:
        """Validate API key"""
        if not self.valid_keys:
            # No authentication configured
            return None

        # Try to get API key from header
        try:
            api_key = await self.api_key_header(api_key)
        except HTTPException:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
                )
            return None

        # Validate API key
        if api_key in self.valid_keys:
            key_info = self.valid_keys[api_key]
            logger.info(f"API key authenticated: {key_info['name']}")
            return key_info

        if self.auto_error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        return None

    def generate_api_key(self, name: str = "generated") -> str:
        """Generate a new API key"""
        # Create a secure random key
        key = secrets.token_urlsafe(32)

        # Store key info
        self.valid_keys[key] = {
            "name": name,
            "permissions": ["read", "write"],
            "created_at": datetime.now().isoformat(),
        }

        logger.info(f"Generated new API key: {name}")
        return key


class JWTAuth:
    """JWT token authentication"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expire_hours: int = 24,
        auto_error: bool = True,
    ):
        self.secret_key = secret_key or os.environ.get("JWT_SECRET_KEY")
        self.algorithm = algorithm
        self.token_expire_hours = token_expire_hours
        self.auto_error = auto_error
        self.bearer_scheme = HTTPBearer(auto_error=auto_error)

        if not self.secret_key:
            # Generate a random secret key if none provided
            self.secret_key = secrets.token_urlsafe(32)
            logger.warning(
                "No JWT secret key configured - using random key (not suitable for production)"
            )

    def create_access_token(
        self, subject: str, permissions: list = None, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.token_expire_hours)

        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.utcnow(),
            "permissions": permissions or ["read"],
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.info(f"Created JWT token for subject: {subject}")

        return token

    def verify_token(self, token: str) -> Optional[dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check expiration
            if payload.get("exp", 0) < time.time():
                logger.warning("JWT token expired")
                return None

            return payload

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
    ) -> dict[str, Any]:
        """Validate JWT token from Authorization header"""
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        payload = self.verify_token(credentials.credentials)

        if not payload:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        return payload


class AuthManager:
    """Unified authentication manager supporting multiple methods"""

    def __init__(self):
        self.api_key_auth = APIKeyAuth(auto_error=False)
        self.jwt_auth = JWTAuth(auto_error=False)

        # Determine authentication method from environment
        self.auth_method = os.environ.get("AUTH_METHOD", "none").lower()

        logger.info(f"Authentication method: {self.auth_method}")

    async def authenticate(
        self, api_key: Optional[str] = None, token: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Authenticate using configured method"""

        if self.auth_method == "none":
            return {"method": "none", "authenticated": False}

        elif self.auth_method == "api_key":
            auth_result = await self.api_key_auth(api_key)
            if auth_result:
                return {"method": "api_key", "authenticated": True, **auth_result}

        elif self.auth_method == "jwt":
            if token:
                # Create credentials object for JWT auth
                from fastapi.security import HTTPAuthorizationCredentials

                credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                auth_result = await self.jwt_auth(credentials)
                if auth_result:
                    return {"method": "jwt", "authenticated": True, **auth_result}

        elif self.auth_method == "hybrid":
            # Try API key first, then JWT
            api_key_result = await self.api_key_auth(api_key)
            if api_key_result:
                return {"method": "api_key", "authenticated": True, **api_key_result}

            if token:
                from fastapi.security import HTTPAuthorizationCredentials

                credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
                jwt_result = await self.jwt_auth(credentials)
                if jwt_result:
                    return {"method": "jwt", "authenticated": True, **jwt_result}

        # Authentication failed
        if self.auth_method != "none":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
            )

        return None


# Convenience functions for FastAPI dependencies
def get_api_key_auth():
    """Get API key authentication dependency"""
    return APIKeyAuth()


def get_jwt_auth():
    """Get JWT authentication dependency"""
    return JWTAuth()


def get_auth_manager():
    """Get unified authentication manager"""
    return AuthManager()


def require_permission(permission: str):
    """Decorator to require specific permission"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would need to be implemented based on your specific needs
            # For now, just pass through
            return await func(*args, **kwargs)

        return wrapper

    return decorator
