# Downloader Changelog

All notable changes to the downloader service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] - 2025-10-13

### Fixed
- Fixed 400 Bad Request error by correcting UUID encoding - only double-encode UUIDs with forward slashes, single-encode standard base64 UUIDs with = padding

## [1.0.4] - 2025-10-13

### Fixed
- Fixed 401 Unauthorized error when downloading recordings by using Zoom API endpoint to fetch OAuth-compatible download URLs instead of webhook-provided URLs that require short-lived download_token

## [1.0.3] - 2025-10-13

### Fixed
- Force redeploy to pick up updated Zoom OAuth credentials from Secret Manager

## [1.0.2] - 2025-10-13

### Fixed
- Zoom webhook secret updated for new Zoom account

## [1.0.1] - 2025-10-13

### Fixed
- Zoom webhook secret configuration updated

## [1.0.0] - 2025-10-13

### Added
- Initial release
- Zoom to Dropbox bridge for transcription pipeline
- Cloud Function deployment
- Complete documentation and test coverage

[Unreleased]: https://github.com/mzakany23/video-to-transcript/compare/downloader-v1.0.0...HEAD
