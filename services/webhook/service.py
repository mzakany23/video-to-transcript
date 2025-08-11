"""
High-level webhook service for processing external notifications
"""

from typing import Any, Optional

from ..core.exceptions import ServiceError
from ..core.logging import get_logger
from ..orchestration.service import OrchestrationService
from .cursors import CursorManager
from .tracking import JobTracker

logger = get_logger(__name__)


class WebhookService:
    """
    High-level webhook service that coordinates webhook processing
    """

    def __init__(
        self,
        orchestration_service: OrchestrationService,
        cursor_manager: CursorManager,
        job_tracker: JobTracker,
        supported_formats: Optional[list[str]] = None,
    ):
        """
        Initialize webhook service

        Args:
            orchestration_service: Service for job orchestration
            cursor_manager: Service for managing cursors
            job_tracker: Service for tracking processed jobs
            supported_formats: List of supported file extensions
        """
        self.orchestration = orchestration_service
        self.cursor_manager = cursor_manager
        self.job_tracker = job_tracker

        self.supported_formats = set(
            supported_formats
            or [
                ".mp3",
                ".mp4",
                ".mpeg",
                ".mpga",
                ".m4a",
                ".wav",
                ".webm",
                ".aac",
                ".oga",
                ".ogg",
                ".flac",
                ".mov",
                ".avi",
                ".mkv",
                ".wmv",
                ".flv",
                ".3gp",
            ]
        )

        logger.info(
            f"Initialized WebhookService with {len(self.supported_formats)} supported formats"
        )

    async def process_notification(
        self, notification_data: dict[str, Any], handler_type: str = "dropbox"
    ) -> dict[str, Any]:
        """
        Process a webhook notification

        Args:
            notification_data: Raw notification data from webhook
            handler_type: Type of webhook handler to use

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing {handler_type} webhook notification")

            # Get handler for this notification type
            if handler_type == "dropbox":
                from .handlers.dropbox import DropboxWebhookHandler

                handler = DropboxWebhookHandler(
                    cursor_manager=self.cursor_manager,
                    job_tracker=self.job_tracker,
                    supported_formats=self.supported_formats,
                )
            else:
                raise ServiceError(f"Unknown webhook handler type: {handler_type}")

            # Process the notification to get changed files
            changed_files = await handler.get_changed_files(notification_data)

            if not changed_files:
                logger.info("No new changes found in webhook notification")
                return {
                    "success": True,
                    "message": "No new changes found",
                    "files_processed": 0,
                    "jobs_triggered": 0,
                }

            logger.info(f"Found {len(changed_files)} changed files")

            # Filter out already processed files
            unprocessed_files = []
            for file_info in changed_files:
                file_id = self._generate_file_id(file_info)
                if not await self.job_tracker.is_processed(file_id):
                    unprocessed_files.append(file_info)
                    logger.info(f"Will process: {file_info['name']}")
                else:
                    logger.info(f"Already processed: {file_info['name']}")

            if not unprocessed_files:
                logger.info("All changed files have already been processed")
                return {
                    "success": True,
                    "message": "All files already processed",
                    "files_processed": len(changed_files),
                    "jobs_triggered": 0,
                }

            # Trigger jobs for unprocessed files
            logger.info(f"Triggering jobs for {len(unprocessed_files)} unprocessed files")

            job_results = []
            for file_info in unprocessed_files:
                try:
                    job_id = await self._trigger_job_for_file(file_info)

                    # Mark as processed
                    file_id = self._generate_file_id(file_info)
                    await self.job_tracker.mark_processed(
                        file_id, job_id=job_id, file_info=file_info
                    )

                    job_results.append(
                        {"success": True, "file_name": file_info["name"], "job_id": job_id}
                    )

                except Exception as e:
                    logger.error(f"Failed to trigger job for {file_info['name']}: {str(e)}")
                    job_results.append(
                        {"success": False, "file_name": file_info["name"], "error": str(e)}
                    )

            successful_jobs = sum(1 for r in job_results if r["success"])

            logger.info(f"Successfully triggered {successful_jobs}/{len(job_results)} jobs")

            return {
                "success": True,
                "message": f"Processed {len(changed_files)} files, triggered {successful_jobs} jobs",
                "files_processed": len(changed_files),
                "jobs_triggered": successful_jobs,
                "job_results": job_results,
            }

        except Exception as e:
            logger.error(f"Error processing webhook notification: {str(e)}")
            return {"success": False, "error": str(e), "files_processed": 0, "jobs_triggered": 0}

    async def _trigger_job_for_file(self, file_info: dict[str, Any]) -> str:
        """
        Trigger a transcription job for a specific file

        Args:
            file_info: File information dictionary

        Returns:
            Job ID
        """
        file_name = file_info["name"]
        file_path = file_info["path"]

        logger.info(f"Triggering transcription job for: {file_name}")

        # Use orchestration service to submit job
        job_id = await self.orchestration.submit_transcription_job(
            file_path=file_path,
            file_name=file_name,
            environment={
                "PROCESS_SINGLE_FILE": "true",
                "TARGET_FILE_PATH": file_path,
                "TARGET_FILE_NAME": file_name,
            },
        )

        logger.info(f"Job triggered for {file_name}: {job_id}")
        return job_id

    def _generate_file_id(self, file_info: dict[str, Any]) -> str:
        """
        Generate a unique file ID for tracking

        Args:
            file_info: File information dictionary

        Returns:
            Unique file identifier
        """
        file_path = file_info.get("path", file_info.get("name", ""))
        return file_path.replace("/", "_").replace(" ", "_")

    def is_supported_format(self, file_name: str) -> bool:
        """
        Check if file format is supported

        Args:
            file_name: Name of the file

        Returns:
            True if format is supported
        """
        import os

        file_extension = os.path.splitext(file_name)[1].lower()
        return file_extension in self.supported_formats

    async def get_processing_stats(self) -> dict[str, Any]:
        """
        Get statistics about webhook processing

        Returns:
            Dictionary with processing statistics
        """
        try:
            processed_count = await self.job_tracker.get_processed_count()
            orchestration_info = self.orchestration.get_runner_info()

            return {
                "processed_files": processed_count,
                "supported_formats": list(self.supported_formats),
                "orchestration": orchestration_info,
            }

        except Exception as e:
            logger.error(f"Error getting processing stats: {str(e)}")
            return {"error": str(e)}

    async def reset_processing_state(self, confirm: bool = False) -> dict[str, Any]:
        """
        Reset all processing state (cursors and job tracking)

        Args:
            confirm: Must be True to actually reset

        Returns:
            Dictionary with reset results
        """
        if not confirm:
            return {"success": False, "error": "Reset requires confirmation"}

        try:
            logger.warning("Resetting webhook processing state")

            # Reset cursors and job tracking
            await self.cursor_manager.reset_all_cursors()
            await self.job_tracker.reset_tracking()

            logger.warning("Webhook processing state has been reset")

            return {"success": True, "message": "Processing state reset successfully"}

        except Exception as e:
            logger.error(f"Error resetting processing state: {str(e)}")
            return {"success": False, "error": str(e)}
