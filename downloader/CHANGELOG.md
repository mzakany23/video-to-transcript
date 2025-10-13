# Downloader Changelog

All notable changes to the downloader service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.9] - 2025-10-13

### Changed
- Increased Cloud Function timeout from 5 minutes to 20 minutes to handle large files (1-2 hour recordings, 1-2GB)
- Ensures reliable processing of long recordings without timeout failures
- Memory (512MB) remains sufficient due to streaming downloads and chunked uploads (4MB chunks)

## [1.0.8] - 2025-10-13

### Fixed
- Always double-encode meeting UUIDs for API calls per Zoom requirements
- Use GET /meetings/{uuid}/recordings API (O1 direct lookup) to get OAuth-compatible download URLs
- Webhook download URLs contain embedded tokens that expire - must fetch OAuth URLs from API
- Tested locally and verified working with proper scopes

## [1.0.7] - 2025-10-13

### Fixed
- Use webhook payload recording files directly - download URLs work with OAuth Bearer tokens
- Removed unreliable GET /meetings/{uuid}/recordings API call that was causing 400 errors
- Verified locally that webhook download URLs work correctly with OAuth (302 redirect then 200)

## [1.0.6] - 2025-10-13

### Added
- Added list_all_recordings() method to ZoomClient for debugging available recordings
- Added better error logging that shows Zoom API error codes and messages

### Fixed
- Improved error diagnostics to help troubleshoot API access issues

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
