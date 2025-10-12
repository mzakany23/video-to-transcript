# Worker Changelog

All notable changes to the transcription worker service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2025-10-12

### Fixed
- Job start email now displays correct file size instead of 0.0 MB
- Read TARGET_FILE_SIZE_MB environment variable from webhook

## [1.1.0] - 2025-10-12

### Added
- Audio chunking support for unlimited file sizes (processes files >25MB)
- Job start email notifications to track processing progress
- Sentry error tracking integration for production monitoring
- Semantic versioning for Docker images

### Fixed
- Email recipient parsing - multiple recipients now work correctly
- OpenAI API 413 errors for large audio files (>25MB)
- Compression target reduced from 25MB to 19MB for reliability

### Changed
- Enhanced error handling and logging
- Improved transcription processing pipeline

## [1.0.1] - 2025-08-23

### Added
- Support for all required secrets in configuration
- Generic project configuration (removed hardcoded references)

### Fixed
- Secret management - proper handling of OpenAI and Dropbox credentials
- Folder path synchronization with webhook service

### Changed
- Improved error handling and troubleshooting

## [1.0.0] - 2025-08-09

### Added
- Initial transcription worker implementation
- Email notification system with support for multiple recipients
- Toggle functionality for email notifications
- SMS notification capabilities
- Complete serverless transcription pipeline
- Support for multiple audio/video formats

### Fixed
- Pipeline workflow issues
- Dependency management improvements

[1.1.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.1.1
[1.1.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.1.0
[1.0.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.0.1
[1.0.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/worker-v1.0.0
