# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-08-23

### Added
- Complete Terraform state management and import functionality
- Support for all required secrets in Terraform configuration (OpenAI, Dropbox OAuth)
- Configurable Dropbox folder paths via terraform.tfvars
- Comprehensive README with full deployment instructions
- Generic project configuration (removed hardcoded project references)

### Fixed
- Terraform state recovery after accidental local state deletion
- Secret management - proper import of existing secrets into Terraform state
- Folder path configuration mismatch (webhook now uses correct paths)
- Made terraform.tfvars generic for public release

### Changed
- Updated README to be project-agnostic for public use
- Improved Terraform configuration with proper variable structure
- Enhanced error handling and troubleshooting documentation

### Infrastructure
- Full Terraform state import and recovery
- Proper secret versioning and management
- Cloud Function and Cloud Run job path synchronization

## [1.0.0] - 2025-08-09

### Added
- Email notification system with support for multiple recipients
- Toggle functionality for email notifications
- SMS notification capabilities
- Automated Dropbox authentication integration
- Complete serverless transcription pipeline
- Webhook operation handling

### Changed
- Improved folder structure and organization
- Refactored directory structure for better maintainability
- Updated README documentation

### Fixed
- Webhook operation name bug
- Pipeline workflow issues
- Dependency management improvements
- Terraform configuration fixes
- Webhook flooding prevention

### Infrastructure
- Terraform deployment configuration
- Google Cloud Functions setup
- Serverless architecture implementation

[1.0.1]: https://github.com/mzakany23/transcripts/releases/tag/v1.0.1
[1.0.0]: https://github.com/mzakany23/transcripts/releases/tag/v1.0.0