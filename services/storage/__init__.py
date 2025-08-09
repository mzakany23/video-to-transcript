"""
Storage service with pluggable providers
"""

from .service import StorageService
from .providers.dropbox import DropboxStorageProvider

__all__ = [
    "StorageService",
    "DropboxStorageProvider",
]