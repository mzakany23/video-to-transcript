"""
Storage service with pluggable providers
"""

from .providers.dropbox import DropboxStorageProvider
from .service import StorageService

__all__ = [
    "StorageService",
    "DropboxStorageProvider",
]
