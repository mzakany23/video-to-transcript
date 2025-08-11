"""
Configuration validation and migration tools
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Configuration validation error"""

    field: str
    error: str
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationResult:
    """Configuration validation result"""

    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]
    provider_checks: dict[str, bool]


class ConfigurationValidator:
    """Validates configuration settings"""

    REQUIRED_ENV_VARS = {
        "gcs": ["GOOGLE_APPLICATION_CREDENTIALS", "PROJECT_ID"],
        "openai": ["OPENAI_API_KEY"],
        "cloud_run": ["PROJECT_ID", "REGION"],
    }

    VALID_PROVIDERS = {
        "storage": ["local", "gcs", "dropbox"],
        "transcription": ["openai"],
        "job_runner": ["local", "cloud_run"],
        "notification": ["email", "slack"],
    }

    def __init__(self, settings: Settings):
        self.settings = settings

    def validate(self) -> ValidationResult:
        """Validate configuration"""
        errors = []
        warnings = []
        provider_checks = {}

        # Validate provider selections
        errors.extend(self._validate_providers())

        # Validate environment variables
        errors.extend(self._validate_environment_vars())

        # Validate file paths
        errors.extend(self._validate_paths())

        # Validate provider configurations
        provider_errors, provider_results = self._validate_provider_configs()
        errors.extend(provider_errors)
        provider_checks.update(provider_results)

        # Validate API configurations
        warnings.extend(self._validate_api_config())

        # Check for deprecated settings
        warnings.extend(self._check_deprecated_settings())

        valid = len([e for e in errors if e.severity == "error"]) == 0

        return ValidationResult(
            valid=valid, errors=errors, warnings=warnings, provider_checks=provider_checks
        )

    def _validate_providers(self) -> list[ValidationError]:
        """Validate provider selections"""
        errors = []

        for provider_type, valid_providers in self.VALID_PROVIDERS.items():
            setting_name = f"{provider_type}_provider"
            selected = getattr(self.settings, setting_name, None)

            if not selected:
                errors.append(
                    ValidationError(
                        field=setting_name, error=f"{setting_name} is required", severity="error"
                    )
                )
            elif selected not in valid_providers:
                errors.append(
                    ValidationError(
                        field=setting_name,
                        error=f"Invalid {setting_name}: {selected}. Must be one of: {valid_providers}",
                        severity="error",
                    )
                )

        return errors

    def _validate_environment_vars(self) -> list[ValidationError]:
        """Validate required environment variables"""
        errors = []

        # Check provider-specific environment variables
        providers_to_check = [
            self.settings.storage_provider,
            self.settings.transcription_provider,
            self.settings.job_runner,
            self.settings.notification_provider,
        ]

        for provider in providers_to_check:
            if provider in self.REQUIRED_ENV_VARS:
                for env_var in self.REQUIRED_ENV_VARS[provider]:
                    if not os.environ.get(env_var):
                        errors.append(
                            ValidationError(
                                field=env_var,
                                error=f"Environment variable {env_var} is required for {provider} provider",
                                severity="error",
                            )
                        )

        return errors

    def _validate_paths(self) -> list[ValidationError]:
        """Validate file and directory paths"""
        errors = []

        # Validate credentials paths
        gcs_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if gcs_creds and not os.path.exists(gcs_creds):
            errors.append(
                ValidationError(
                    field="GOOGLE_APPLICATION_CREDENTIALS",
                    error=f"Credentials file not found: {gcs_creds}",
                    severity="error",
                )
            )

        # Validate local storage paths
        if self.settings.storage_provider == "local":
            local_config = self.settings.storage_configs.get("local")
            if local_config:
                base_path = local_config.config.get("base_path", "./data")
                base_dir = Path(base_path).parent

                if not base_dir.exists():
                    errors.append(
                        ValidationError(
                            field="storage.local.base_path",
                            error=f"Base directory does not exist: {base_dir}",
                            severity="warning",
                        )
                    )

        return errors

    def _validate_provider_configs(self) -> tuple[list[ValidationError], dict[str, bool]]:
        """Validate provider-specific configurations"""
        errors = []
        provider_checks = {}

        # Validate storage provider
        storage_valid = self._validate_storage_provider()
        provider_checks["storage"] = storage_valid
        if not storage_valid:
            errors.append(
                ValidationError(
                    field="storage_provider",
                    error=f"Storage provider {self.settings.storage_provider} configuration invalid",
                    severity="error",
                )
            )

        # Validate transcription provider
        transcription_valid = self._validate_transcription_provider()
        provider_checks["transcription"] = transcription_valid
        if not transcription_valid:
            errors.append(
                ValidationError(
                    field="transcription_provider",
                    error=f"Transcription provider {self.settings.transcription_provider} configuration invalid",
                    severity="error",
                )
            )

        # Validate job runner
        job_runner_valid = self._validate_job_runner()
        provider_checks["job_runner"] = job_runner_valid
        if not job_runner_valid:
            errors.append(
                ValidationError(
                    field="job_runner",
                    error=f"Job runner {self.settings.job_runner} configuration invalid",
                    severity="error",
                )
            )

        return errors, provider_checks

    def _validate_storage_provider(self) -> bool:
        """Validate storage provider configuration"""
        provider = self.settings.storage_provider

        if provider == "local":
            return True  # Local storage always works
        elif provider == "gcs":
            return bool(
                os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("PROJECT_ID")
            )
        elif provider == "dropbox":
            return bool(os.environ.get("DROPBOX_ACCESS_TOKEN"))

        return False

    def _validate_transcription_provider(self) -> bool:
        """Validate transcription provider configuration"""
        provider = self.settings.transcription_provider

        if provider == "openai":
            return bool(os.environ.get("OPENAI_API_KEY"))

        return False

    def _validate_job_runner(self) -> bool:
        """Validate job runner configuration"""
        provider = self.settings.job_runner

        if provider == "local":
            return True  # Local runner always works
        elif provider == "cloud_run":
            return bool(os.environ.get("PROJECT_ID") and os.environ.get("REGION"))

        return False

    def _validate_api_config(self) -> list[ValidationError]:
        """Validate API configuration"""
        warnings = []

        # Check for missing optional configurations
        if not os.environ.get("LOG_LEVEL"):
            warnings.append(
                ValidationError(
                    field="LOG_LEVEL",
                    error="LOG_LEVEL not set, defaulting to INFO",
                    severity="warning",
                )
            )

        return warnings

    def _check_deprecated_settings(self) -> list[ValidationError]:
        """Check for deprecated configuration settings"""
        warnings = []

        # Check for old environment variable names
        deprecated_vars = {
            "GOOGLE_CLOUD_PROJECT": "PROJECT_ID",
            "GCP_PROJECT": "PROJECT_ID",
            "OPENAI_SECRET_KEY": "OPENAI_API_KEY",
        }

        for old_var, new_var in deprecated_vars.items():
            if os.environ.get(old_var) and not os.environ.get(new_var):
                warnings.append(
                    ValidationError(
                        field=old_var,
                        error=f"Environment variable {old_var} is deprecated. Use {new_var} instead.",
                        severity="warning",
                    )
                )

        return warnings


class ConfigurationMigrator:
    """Handles configuration migrations between versions"""

    CURRENT_VERSION = "1.0.0"

    MIGRATIONS = {
        "0.1.0": "_migrate_from_0_1_0",
        "0.2.0": "_migrate_from_0_2_0",
    }

    def __init__(self):
        self.backup_dir = Path("./config_backups")
        self.backup_dir.mkdir(exist_ok=True)

    def migrate_configuration(self, config_path: Path) -> bool:
        """Migrate configuration file to current version"""
        try:
            # Load existing configuration
            with open(config_path) as f:
                config_data = json.load(f)

            current_version = config_data.get("version", "0.1.0")

            if current_version == self.CURRENT_VERSION:
                logger.info("Configuration is already at current version")
                return True

            # Create backup
            self._create_backup(config_path, config_data)

            # Apply migrations
            migrated_data = self._apply_migrations(config_data, current_version)

            # Update version
            migrated_data["version"] = self.CURRENT_VERSION
            migrated_data["migrated_at"] = datetime.now().isoformat()

            # Save migrated configuration
            with open(config_path, "w") as f:
                json.dump(migrated_data, f, indent=2)

            logger.info(f"Configuration migrated from {current_version} to {self.CURRENT_VERSION}")
            return True

        except Exception as e:
            logger.error(f"Configuration migration failed: {str(e)}")
            return False

    def _create_backup(self, config_path: Path, config_data: dict[str, Any]):
        """Create backup of configuration before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{config_path.stem}_backup_{timestamp}.json"

        with open(backup_path, "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Configuration backup created: {backup_path}")

    def _apply_migrations(self, config_data: dict[str, Any], from_version: str) -> dict[str, Any]:
        """Apply all necessary migrations"""
        current_data = config_data.copy()

        # Determine migration path
        versions_to_migrate = []
        found_start = False

        for version in self.MIGRATIONS.keys():
            if version == from_version:
                found_start = True
                continue
            if found_start:
                versions_to_migrate.append(version)

        # Apply migrations in order
        for version in versions_to_migrate:
            migration_method = getattr(self, self.MIGRATIONS[version])
            current_data = migration_method(current_data)
            logger.info(f"Applied migration for version {version}")

        return current_data

    def _migrate_from_0_1_0(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from version 0.1.0"""
        migrated = config_data.copy()

        # Rename old storage provider names
        storage_renames = {"google_cloud": "gcs", "google_storage": "gcs"}

        storage_provider = migrated.get("storage_provider")
        if storage_provider in storage_renames:
            migrated["storage_provider"] = storage_renames[storage_provider]
            logger.info(
                f"Renamed storage provider: {storage_provider} -> {storage_renames[storage_provider]}"
            )

        # Add new required fields
        if "notification_provider" not in migrated:
            migrated["notification_provider"] = "email"
            logger.info("Added default notification_provider: email")

        return migrated

    def _migrate_from_0_2_0(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from version 0.2.0"""
        migrated = config_data.copy()

        # Migrate job runner configurations
        if "job_runner_configs" in migrated:
            job_configs = migrated["job_runner_configs"]

            # Update Cloud Run configuration structure
            if "cloud_run" in job_configs:
                old_config = job_configs["cloud_run"]
                new_config = {
                    "config": {
                        "project_id": old_config.get("project_id"),
                        "region": old_config.get("region", "us-east1"),
                        "job_name": old_config.get("job_name", "transcription-worker"),
                        "image": old_config.get("image"),
                        "cpu": old_config.get("cpu", 1),
                        "memory": old_config.get("memory", "2Gi"),
                        "max_retries": old_config.get("max_retries", 3),
                    }
                }
                migrated["job_runner_configs"]["cloud_run"] = new_config
                logger.info("Updated Cloud Run configuration structure")

        return migrated


def validate_configuration(settings: Settings) -> ValidationResult:
    """Convenience function to validate configuration"""
    validator = ConfigurationValidator(settings)
    return validator.validate()


def migrate_configuration_file(config_path: str) -> bool:
    """Convenience function to migrate configuration file"""
    migrator = ConfigurationMigrator()
    return migrator.migrate_configuration(Path(config_path))


def generate_sample_config(output_path: str = "config_sample.json") -> bool:
    """Generate sample configuration file"""
    try:
        sample_settings = Settings(
            storage_provider="local",
            transcription_provider="openai",
            job_runner="local",
            notification_provider="email",
            environment="development",
            log_level="INFO",
        )

        sample_settings.to_file(output_path)
        logger.info(f"Sample configuration generated: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to generate sample configuration: {str(e)}")
        return False
