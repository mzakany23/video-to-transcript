#!/usr/bin/env python3
"""
Configuration management CLI tool
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from services.config.settings import Settings
from services.config.validator import (
    ConfigurationValidator,
    ConfigurationMigrator,
    ValidationResult,
    generate_sample_config
)


def format_validation_result(result: ValidationResult) -> str:
    """Format validation result for display"""
    output = []
    
    if result.valid:
        output.append("✅ Configuration is valid")
    else:
        output.append("❌ Configuration has errors")
    
    output.append("")
    
    # Show errors
    if result.errors:
        output.append("Errors:")
        for error in result.errors:
            severity_icon = "🔴" if error.severity == "error" else "🟡"
            output.append(f"  {severity_icon} {error.field}: {error.error}")
        output.append("")
    
    # Show warnings  
    if result.warnings:
        output.append("Warnings:")
        for warning in result.warnings:
            output.append(f"  🟡 {warning.field}: {warning.error}")
        output.append("")
    
    # Show provider checks
    if result.provider_checks:
        output.append("Provider Status:")
        for provider, status in result.provider_checks.items():
            status_icon = "✅" if status else "❌"
            output.append(f"  {status_icon} {provider}: {'OK' if status else 'Failed'}")
        output.append("")
    
    return "\n".join(output)


def validate_command(args):
    """Handle validate command"""
    try:
        if args.config_file:
            settings = Settings.from_file(args.config_file)
            print(f"Validating configuration from: {args.config_file}")
        else:
            settings = Settings.from_env()
            print("Validating configuration from environment variables")
        
        validator = ConfigurationValidator(settings)
        result = validator.validate()
        
        print(format_validation_result(result))
        
        if args.json:
            json_output = {
                "valid": result.valid,
                "errors": [
                    {"field": e.field, "error": e.error, "severity": e.severity}
                    for e in result.errors
                ],
                "warnings": [
                    {"field": w.field, "error": w.error, "severity": w.severity}
                    for w in result.warnings
                ],
                "provider_checks": result.provider_checks
            }
            print("\nJSON Output:")
            print(json.dumps(json_output, indent=2))
        
        # Exit with error code if validation failed
        sys.exit(0 if result.valid else 1)
        
    except Exception as e:
        print(f"❌ Validation failed: {str(e)}")
        sys.exit(1)


def migrate_command(args):
    """Handle migrate command"""
    try:
        config_path = Path(args.config_file)
        
        if not config_path.exists():
            print(f"❌ Configuration file not found: {config_path}")
            sys.exit(1)
        
        print(f"Migrating configuration file: {config_path}")
        
        migrator = ConfigurationMigrator()
        success = migrator.migrate_configuration(config_path)
        
        if success:
            print("✅ Migration completed successfully")
            
            # Validate after migration
            settings = Settings.from_file(str(config_path))
            validator = ConfigurationValidator(settings)
            result = validator.validate()
            
            if result.valid:
                print("✅ Migrated configuration is valid")
            else:
                print("⚠️ Migrated configuration has issues:")
                print(format_validation_result(result))
        else:
            print("❌ Migration failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)


def generate_command(args):
    """Handle generate command"""
    try:
        output_path = args.output or "config_sample.json"
        
        if Path(output_path).exists() and not args.force:
            print(f"❌ File already exists: {output_path}")
            print("Use --force to overwrite")
            sys.exit(1)
        
        success = generate_sample_config(output_path)
        
        if success:
            print(f"✅ Sample configuration generated: {output_path}")
            
            # Show sample content
            with open(output_path, 'r') as f:
                config_data = json.load(f)
            
            print("\nSample configuration:")
            print(json.dumps(config_data, indent=2))
        else:
            print("❌ Failed to generate sample configuration")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Generation failed: {str(e)}")
        sys.exit(1)


def show_command(args):
    """Handle show command"""
    try:
        if args.config_file:
            settings = Settings.from_file(args.config_file)
            source = f"file: {args.config_file}"
        else:
            settings = Settings.from_env()
            source = "environment variables"
        
        print(f"Configuration from {source}:\n")
        
        # Show main settings
        main_settings = {
            "storage_provider": settings.storage_provider,
            "transcription_provider": settings.transcription_provider,
            "job_runner": settings.job_runner,
            "notification_provider": settings.notification_provider,
            "environment": settings.environment,
            "log_level": settings.log_level
        }
        
        print("Main Settings:")
        for key, value in main_settings.items():
            print(f"  {key}: {value}")
        
        print("\nProvider Configurations:")
        
        # Show storage configs
        if hasattr(settings, 'storage_configs'):
            for provider, config in settings.storage_configs.items():
                print(f"  storage.{provider}: {config.config}")
        
        # Show job runner configs
        if hasattr(settings, 'job_runner_configs'):
            for provider, config in settings.job_runner_configs.items():
                print(f"  job_runner.{provider}: {config.config}")
        
        if args.json:
            # Export full configuration as JSON
            config_dict = settings.to_dict()
            print(f"\nFull configuration (JSON):")
            print(json.dumps(config_dict, indent=2, default=str))
            
    except Exception as e:
        print(f"❌ Failed to show configuration: {str(e)}")
        sys.exit(1)


def init_command(args):
    """Handle init command"""
    try:
        config_path = args.config_file or "config.json"
        
        if Path(config_path).exists() and not args.force:
            print(f"❌ Configuration file already exists: {config_path}")
            print("Use --force to overwrite")
            sys.exit(1)
        
        print("🚀 Initializing transcription services configuration")
        print()
        
        # Interactive configuration
        storage_provider = input("Storage provider (local/gcs/dropbox) [local]: ").strip() or "local"
        transcription_provider = input("Transcription provider (openai) [openai]: ").strip() or "openai"
        job_runner = input("Job runner (local/cloud_run) [local]: ").strip() or "local"
        environment = input("Environment (development/production) [development]: ").strip() or "development"
        
        # Create settings
        settings = Settings(
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            job_runner=job_runner,
            notification_provider="email",
            environment=environment,
            log_level="INFO"
        )
        
        # Save configuration
        settings.to_file(config_path)
        print(f"\n✅ Configuration saved to: {config_path}")
        
        # Validate configuration
        validator = ConfigurationValidator(settings)
        result = validator.validate()
        
        print("\nValidation Results:")
        print(format_validation_result(result))
        
        if not result.valid:
            print("❌ Configuration needs attention before use")
            print("\nNext steps:")
            print("1. Set required environment variables")
            print("2. Run: python cli/config_manager.py validate")
            print("3. Fix any errors and re-validate")
        else:
            print("🎉 Configuration is ready to use!")
            
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Transcription Services Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate current environment configuration
  python cli/config_manager.py validate
  
  # Validate configuration file
  python cli/config_manager.py validate --config config.json
  
  # Create interactive configuration
  python cli/config_manager.py init
  
  # Migrate configuration to latest version
  python cli/config_manager.py migrate config.json
  
  # Generate sample configuration
  python cli/config_manager.py generate --output sample.json
  
  # Show current configuration
  python cli/config_manager.py show --json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument(
        '--config-file', '-c',
        help='Configuration file path (uses environment if not specified)'
    )
    validate_parser.add_argument(
        '--json', 
        action='store_true',
        help='Output results as JSON'
    )
    validate_parser.set_defaults(func=validate_command)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate configuration file')
    migrate_parser.add_argument('config_file', help='Configuration file to migrate')
    migrate_parser.set_defaults(func=migrate_command)
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate sample configuration')
    generate_parser.add_argument(
        '--output', '-o',
        help='Output file path (default: config_sample.json)'
    )
    generate_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing file'
    )
    generate_parser.set_defaults(func=generate_command)
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show current configuration')
    show_parser.add_argument(
        '--config-file', '-c',
        help='Configuration file path (uses environment if not specified)'
    )
    show_parser.add_argument(
        '--json',
        action='store_true', 
        help='Output configuration as JSON'
    )
    show_parser.set_defaults(func=show_command)
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize configuration interactively')
    init_parser.add_argument(
        '--config-file', '-c',
        help='Configuration file path (default: config.json)'
    )
    init_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing configuration file'
    )
    init_parser.set_defaults(func=init_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()