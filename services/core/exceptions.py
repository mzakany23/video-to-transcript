"""
Custom exceptions for the service system
"""


class ServiceError(Exception):
    """Base exception for all service errors"""

    pass


class StorageError(ServiceError):
    """Exception for storage-related errors"""

    pass


class TranscriptionError(ServiceError):
    """Exception for transcription-related errors"""

    pass


class JobError(ServiceError):
    """Exception for job execution errors"""

    pass


class NotificationError(ServiceError):
    """Exception for notification errors"""

    pass


class ConfigurationError(ServiceError):
    """Exception for configuration errors"""

    pass


class AuthenticationError(ServiceError):
    """Exception for authentication errors"""

    pass
