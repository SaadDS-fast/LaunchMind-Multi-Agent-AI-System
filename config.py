import os

from dotenv import load_dotenv

from logging_utils import log, log_skip


REQUIRED_ENV_VARS = ("GITHUB_TOKEN", "GITHUB_REPO")
OPTIONAL_ENV_VARS = ("SENDGRID_API_KEY", "SLACK_BOT_TOKEN")


class ConfigurationError(RuntimeError):
    """Raised when required environment configuration is missing."""


def validate_environment() -> None:
    """Validate required configuration and report optional integration status."""
    load_dotenv()

    missing_required = [key for key in REQUIRED_ENV_VARS if not os.getenv(key)]
    if missing_required:
        joined = ", ".join(missing_required)
        raise ConfigurationError(f"Missing required environment variable(s): {joined}")

    for key in OPTIONAL_ENV_VARS:
        if not os.getenv(key):
            log_skip("Config", f"{key} not configured; related integration will be skipped.")

    log("Config", "Environment validation completed.")
