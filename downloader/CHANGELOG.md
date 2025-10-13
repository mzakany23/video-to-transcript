# Downloader Changelog

All notable changes to the downloader service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial implementation of Zoom downloader service
- Zoom webhook handler with signature verification
- Server-to-Server OAuth authentication with Zoom API
- Streaming download of MP4 recordings from Zoom cloud
- Chunked upload to Dropbox for large files
- State tracking to prevent duplicate processing
- Sentry error tracking integration
- Comprehensive test suite with 22 unit tests
- Cloud Storage integration for recording metadata
- Support for `recording.completed` webhook events
- Endpoint validation challenge support
- Progress logging for large file operations

### Security
- HMAC-SHA256 signature verification for all Zoom webhooks
- Secure credential storage in GCP Secret Manager
- OAuth refresh token support for Dropbox

## [1.0.0] - TBD

### Added
- Initial release
- Zoom to Dropbox bridge for transcription pipeline
- Cloud Function deployment
- Complete documentation and test coverage

[Unreleased]: https://github.com/mzakany23/video-to-transcript/compare/downloader-v1.0.0...HEAD
