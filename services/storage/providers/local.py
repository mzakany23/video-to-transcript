"""
Local filesystem implementation of StorageProvider
"""

import asyncio
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ...core.exceptions import StorageError
from ...core.interfaces import StorageProvider
from ...core.logging import get_logger
from ...core.models import BatchResult, DownloadResult, FileInfo, UploadResult

logger = get_logger(__name__)


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem implementation of storage provider
    Suitable for testing and development environments
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local storage provider

        Args:
            base_path: Base directory for file operations
        """
        self.base_path = Path(base_path) if base_path else Path.cwd() / "local_storage"
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized LocalStorageProvider: {self.base_path}")

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve relative path to absolute path within base directory

        Args:
            file_path: Relative file path

        Returns:
            Absolute Path object
        """
        # Remove leading slash if present to ensure relative path
        clean_path = file_path.lstrip("/")
        resolved = self.base_path / clean_path

        # Ensure path is within base directory (security check)
        try:
            resolved.resolve().relative_to(self.base_path.resolve())
        except ValueError:
            raise StorageError(f"Path outside base directory not allowed: {file_path}")

        return resolved

    async def download(self, source_path: str, destination_path: str) -> DownloadResult:
        """
        Copy file from storage location to destination

        Args:
            source_path: Source file path (relative to base_path)
            destination_path: Destination file path (absolute)

        Returns:
            DownloadResult with metadata
        """
        try:
            source = self._resolve_path(source_path)
            dest = Path(destination_path)

            # Check if source exists
            if not source.exists():
                return DownloadResult(
                    success=False,
                    error=f"Source file not found: {source_path}",
                    metadata={"source_path": str(source)},
                )

            # Ensure destination directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            start_time = datetime.now()
            shutil.copy2(source, dest)
            download_time = (datetime.now() - start_time).total_seconds()

            # Get file info
            file_size = dest.stat().st_size

            logger.info(f"Downloaded locally: {source} -> {dest} ({file_size} bytes)")

            return DownloadResult(
                success=True,
                file_path=str(dest),
                file_size=file_size,
                download_time_seconds=download_time,
                metadata={"source_path": str(source), "operation": "local_copy"},
            )

        except Exception as e:
            error_msg = f"Local download failed: {str(e)}"
            logger.error(error_msg)
            return DownloadResult(
                success=False, error=error_msg, metadata={"source_path": source_path}
            )

    async def upload(self, source_path: str, destination_path: str) -> UploadResult:
        """
        Copy file from source to storage location

        Args:
            source_path: Source file path (absolute)
            destination_path: Destination path (relative to base_path)

        Returns:
            UploadResult with metadata
        """
        try:
            source = Path(source_path)
            dest = self._resolve_path(destination_path)

            # Check if source exists
            if not source.exists():
                return UploadResult(
                    success=False,
                    error=f"Source file not found: {source_path}",
                    metadata={"destination_path": str(dest)},
                )

            # Ensure destination directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            start_time = datetime.now()
            shutil.copy2(source, dest)
            upload_time = (datetime.now() - start_time).total_seconds()

            # Get file info
            file_size = source.stat().st_size

            logger.info(f"Uploaded locally: {source} -> {dest} ({file_size} bytes)")

            return UploadResult(
                success=True,
                file_path=str(dest),
                file_size=file_size,
                upload_time_seconds=upload_time,
                metadata={"source_path": str(source), "operation": "local_copy"},
            )

        except Exception as e:
            error_msg = f"Local upload failed: {str(e)}"
            logger.error(error_msg)
            return UploadResult(
                success=False, error=error_msg, metadata={"source_path": source_path}
            )

    async def list_files(
        self, prefix: Optional[str] = None, limit: Optional[int] = None
    ) -> list[FileInfo]:
        """
        List files in storage

        Args:
            prefix: Path prefix to filter by
            limit: Maximum number of files to return

        Returns:
            List of FileInfo objects
        """
        try:
            search_path = self.base_path
            if prefix:
                search_path = self._resolve_path(prefix)
                if not search_path.exists():
                    return []

            file_infos = []

            # Walk through directory tree
            if search_path.is_dir():
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        # Calculate relative path from base_path
                        relative_path = file_path.relative_to(self.base_path)

                        stat = file_path.stat()
                        file_info = FileInfo(
                            name=file_path.name,
                            path=str(relative_path),
                            size=stat.st_size,
                            modified_at=datetime.fromtimestamp(stat.st_mtime),
                            metadata={
                                "absolute_path": str(file_path),
                                "created_at": datetime.fromtimestamp(stat.st_ctime),
                                "permissions": oct(stat.st_mode)[-3:],
                            },
                        )
                        file_infos.append(file_info)

                        # Apply limit
                        if limit and len(file_infos) >= limit:
                            break

            elif search_path.is_file():
                # Single file
                relative_path = search_path.relative_to(self.base_path)
                stat = search_path.stat()
                file_info = FileInfo(
                    name=search_path.name,
                    path=str(relative_path),
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    metadata={
                        "absolute_path": str(search_path),
                        "created_at": datetime.fromtimestamp(stat.st_ctime),
                        "permissions": oct(stat.st_mode)[-3:],
                    },
                )
                file_infos.append(file_info)

            # Sort by modification time (newest first)
            file_infos.sort(key=lambda x: x.modified_at, reverse=True)

            logger.info(f"Listed {len(file_infos)} files from local storage")
            return file_infos

        except Exception as e:
            logger.error(f"Local file listing failed: {str(e)}")
            raise StorageError(f"Failed to list files: {str(e)}")

    async def delete(self, file_path: str) -> bool:
        """
        Delete file from storage

        Args:
            file_path: File path (relative to base_path)

        Returns:
            True if deleted successfully
        """
        try:
            target = self._resolve_path(file_path)

            if not target.exists():
                logger.warning(f"File not found for deletion: {file_path}")
                return False

            if target.is_file():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)

            logger.info(f"Deleted from local storage: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Local deletion failed for {file_path}: {str(e)}")
            return False

    async def exists(self, file_path: str) -> bool:
        """
        Check if file exists in storage

        Args:
            file_path: File path (relative to base_path)

        Returns:
            True if file exists
        """
        try:
            target = self._resolve_path(file_path)
            return target.exists()
        except Exception as e:
            logger.error(f"Local existence check failed for {file_path}: {str(e)}")
            return False

    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """
        Get detailed information about a file

        Args:
            file_path: File path (relative to base_path)

        Returns:
            FileInfo object or None if not found
        """
        try:
            target = self._resolve_path(file_path)

            if not target.exists() or not target.is_file():
                return None

            stat = target.stat()
            return FileInfo(
                name=target.name,
                path=file_path,
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                metadata={
                    "absolute_path": str(target),
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "accessed_at": datetime.fromtimestamp(stat.st_atime),
                    "permissions": oct(stat.st_mode)[-3:],
                    "inode": stat.st_ino,
                    "device": stat.st_dev,
                },
            )

        except Exception as e:
            logger.error(f"Local file info failed for {file_path}: {str(e)}")
            return None

    async def download_batch(
        self, file_paths: list[str], destination_dir: str, max_concurrent: int = 5
    ) -> BatchResult:
        """
        Download multiple files concurrently

        Args:
            file_paths: List of file paths (relative to base_path)
            destination_dir: Local directory for downloads
            max_concurrent: Maximum concurrent downloads (ignored for local)

        Returns:
            BatchResult with individual results
        """
        # For local storage, we don't need to limit concurrency as much
        # since we're just copying files locally

        tasks = []
        for file_path in file_paths:
            dest_path = os.path.join(destination_dir, os.path.basename(file_path))
            tasks.append(self.download(file_path, dest_path))

        # Execute downloads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append({"file_path": file_paths[i], "error": str(result)})
            elif result.success:
                successful.append(result)
            else:
                failed.append({"file_path": file_paths[i], "error": result.error})

        logger.info(f"Local batch download: {len(successful)} successful, {len(failed)} failed")

        return BatchResult(successful=successful, failed=failed, total_processed=len(file_paths))

    def get_base_path(self) -> str:
        """
        Get the base path for this storage provider

        Returns:
            Absolute path to base directory
        """
        return str(self.base_path.resolve())

    def get_storage_info(self) -> dict[str, Any]:
        """
        Get information about the storage

        Returns:
            Dictionary with storage information
        """
        try:
            stat = self.base_path.stat()
            total_size = sum(f.stat().st_size for f in self.base_path.rglob("*") if f.is_file())
            file_count = sum(1 for f in self.base_path.rglob("*") if f.is_file())

            return {
                "provider": "local",
                "base_path": str(self.base_path),
                "total_size_bytes": total_size,
                "file_count": file_count,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "free_space_bytes": shutil.disk_usage(self.base_path).free,
            }

        except Exception as e:
            logger.error(f"Failed to get storage info: {str(e)}")
            return {"provider": "local", "base_path": str(self.base_path), "error": str(e)}
