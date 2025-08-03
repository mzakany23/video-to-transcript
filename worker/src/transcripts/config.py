"""
Configuration management for transcription pipeline
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Centralized configuration management"""
    
    # Dropbox Configuration
    DROPBOX_ACCESS_TOKEN: str = os.environ.get("DROPBOX_ACCESS_TOKEN", "")
    DROPBOX_REFRESH_TOKEN: str = os.environ.get("DROPBOX_REFRESH_TOKEN", "")
    DROPBOX_APP_SECRET: str = os.environ.get("DROPBOX_APP_SECRET", "")
    DROPBOX_APP_KEY: str = os.environ.get("DROPBOX_APP_KEY", "ry0wtf3rwnxda14")
    
    # Dropbox Folder Structure (scoped to 'jos-transcripts')
    RAW_FOLDER: str = "/jos-transcripts/raw"
    PROCESSED_FOLDER: str = "/jos-transcripts/processed"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = "whisper-1"
    
    # Google Cloud Configuration
    PROJECT_ID: str = os.environ.get("PROJECT_ID", "")
    SECRET_NAME: str = os.environ.get("SECRET_NAME", "openai-api-key")
    GCP_REGION: str = os.environ.get("GCP_REGION", "us-east1")
    
    # Cloud Run Configuration
    TRANSCRIPTION_JOB_NAME: str = os.environ.get("TRANSCRIPTION_JOB_NAME", "transcription-processor-dropbox")
    WEBHOOK_PORT: int = int(os.environ.get("PORT", "8080"))
    
    # File Processing Configuration
    MAX_FILE_SIZE_MB: int = 25  # OpenAI Whisper limit
    MAX_FILES_PER_BATCH: int = int(os.environ.get("MAX_FILES", "10"))
    
    # Audio Processing Configuration
    SUPPORTED_FORMATS = {
        '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
        '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi', '.mkv',
        '.wmv', '.flv', '.3gp'
    }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        required_vars = [
            "OPENAI_API_KEY",
        ]
        
        # Either access token OR (refresh token + app secret) is required
        has_access_token = bool(cls.DROPBOX_ACCESS_TOKEN)
        has_refresh_setup = bool(cls.DROPBOX_REFRESH_TOKEN and cls.DROPBOX_APP_SECRET)
        
        if not (has_access_token or has_refresh_setup):
            required_vars.append("DROPBOX_ACCESS_TOKEN or (DROPBOX_REFRESH_TOKEN + DROPBOX_APP_SECRET)")
        
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        
        return True
    
    @classmethod
    def get_temp_dir(cls) -> Path:
        """Get temporary directory for file processing"""
        return Path("/tmp")
    
    @classmethod
    def is_supported_format(cls, filename: str) -> bool:
        """Check if file format is supported for transcription"""
        return Path(filename).suffix.lower() in cls.SUPPORTED_FORMATS