"""
Custom exceptions for the service system
"""


class ServiceException(Exception):
    """Base exception for all service errors"""
    pass


class StorageException(ServiceException):
    """Exception for storage-related errors"""
    pass


class TranscriptionException(ServiceException):
    """Exception for transcription-related errors"""
    pass


class JobException(ServiceException):
    """Exception for job execution errors"""
    pass


class NotificationException(ServiceException):
    """Exception for notification errors"""
    pass


class ConfigurationException(ServiceException):
    """Exception for configuration errors"""
    pass


class AuthenticationException(ServiceException):
    """Exception for authentication errors"""
    pass