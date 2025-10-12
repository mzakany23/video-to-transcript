# Webhook Changelog

All notable changes to the webhook service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2025-10-12

### Fixed
- Dropbox webhook 403 Forbidden errors by adding Cloud Run service IAM binding
- Gen2 Cloud Functions now properly allow unauthenticated invocations (secured via HMAC signature verification)

## [1.2.0] - 2025-10-12

### Added
- Sentry error tracking integration for production monitoring
- Semantic versioning support with VERSION environment variable
- Graceful degradation when Sentry DSN not configured
- Performance monitoring (10% sample rate)

### Changed
- Updated sentry-sdk dependency to >=1.40.0
- Enhanced startup logging with version information

## [1.1.0] - 2025-10-12

### Added
- Complete CI/CD pipeline with GitHub Actions
- Automated deployment workflow
- Enhanced secret management via Terraform
- Dropbox folder path configuration support

### Changed
- Infrastructure now fully managed via Terraform in CI/CD
- Workload Identity Federation for keyless authentication
- Improved error handling and logging

### Fixed
- Webhook flooding prevention
- Folder path configuration synchronization

## [1.0.1] - 2025-08-23

### Added
- Configurable Dropbox folder paths via terraform.tfvars
- Proper secret management in Terraform

### Fixed
- Folder path configuration mismatch with worker service
- Secret versioning in Cloud Function

## [1.0.0] - 2025-08-09

### Added
- Initial webhook handler implementation
- Dropbox webhook verification support
- Cloud Run job triggering functionality
- Automated Dropbox authentication integration

### Fixed
- Webhook operation name bug
- Webhook flooding prevention

[1.2.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/webhook-v1.2.1
[1.2.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/webhook-v1.2.0
[1.1.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/webhook-v1.1.0
[1.0.1]: https://github.com/mzakany23/video-to-transcript/releases/tag/webhook-v1.0.1
[1.0.0]: https://github.com/mzakany23/video-to-transcript/releases/tag/webhook-v1.0.0
