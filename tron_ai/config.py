import logging
import logging.config  # Explicit import for dictConfig
import os
import copy

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar-reasoning-pro")

# --- Logging Configuration ---
# Default logging levels are defined below.
# You can override the level for any logger by setting an environment variable:
# TRON_LOG_LEVEL_<LOGGER_NAME_UPPERCASE>=<LEVEL>
# Note: Dots in logger names are replaced with underscores for env vars.
# Example: TRON_LOG_LEVEL_tron_ai=DEBUG
# Example: TRON_LOG_LEVEL_ROOT=INFO (for the root logger)
# Example: TRON_LOG_LEVEL_tron_ai_MODULES_MCP_MULTI_MCP_CLIENT=DEBUG
# Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Get default levels from environment variables with fallbacks
DEFAULT_ROOT_LEVEL = os.getenv("TRON_LOG_LEVEL_ROOT", "DEBUG")
DEFAULT_APP_LEVEL = os.getenv("TRON_LOG_LEVEL_tron_ai", "DEBUG")
DEFAULT_THIRD_PARTY_LEVEL = os.getenv("TRON_LOG_LEVEL_THIRD_PARTY", "ERROR")
DEFAULT_UTILITY_LEVEL = os.getenv("TRON_LOG_LEVEL_UTILITY", "ERROR")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "rich": {
            "format": os.getenv("TRON_LOG_FORMAT", "%(message)s"),
            "datefmt": os.getenv("TRON_LOG_DATEFMT", "[%X]"),
        },
    },
    "handlers": {
        "rich": {
            "class": "rich.logging.RichHandler",
            "formatter": "rich",
            "level": os.getenv("TRON_LOG_HANDLER_LEVEL", "DEBUG"),
            "rich_tracebacks": os.getenv("TRON_LOG_RICH_TRACEBACKS", "true").lower() == "true",
            "tracebacks_show_locals": os.getenv("TRON_LOG_SHOW_LOCALS", "true").lower() == "true",
        },
        "simple": {
            "class": "logging.StreamHandler",
            "formatter": "rich",
            "level": "CRITICAL",
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["rich"],
            "level": DEFAULT_ROOT_LEVEL,
            "propagate": False,
        },
        "tron_ai": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "adalflow": {
            "handlers": ["rich"],
            "level": DEFAULT_THIRD_PARTY_LEVEL,
            "propagate": False,
        },
        "mcp_client": {
            "handlers": ["rich"],
            "level": DEFAULT_THIRD_PARTY_LEVEL,
            "propagate": False,
        },
        "httpx": {
            "handlers": ["rich"],
            "level": DEFAULT_THIRD_PARTY_LEVEL,
            "propagate": False,
        },
        "openai": {
            "handlers": ["rich"],
            "level": DEFAULT_THIRD_PARTY_LEVEL,
            "propagate": False,
        },
        "asyncio": {
            "handlers": ["simple"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "multi_mcp_client": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "mcp_agent": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "task_executor": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "mcp_queue": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "agent": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "agent_selector": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "tron_ai.cli": {
            "handlers": ["rich"],
            "level": "INFO",
            "propagate": False,
        },
        "tron_ai.config": {
            "handlers": ["rich"],
            "level": DEFAULT_APP_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.llm.LLMClient": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.concurrency.connection_manager": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.concurrency.process_monitor": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.io.file_manager": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.io.file_manager_async": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.io.json": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.io.prompt_loader": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
        "tron_ai.utils.graph.graph": {
            "handlers": ["rich"],
            "level": DEFAULT_UTILITY_LEVEL,
            "propagate": False,
        },
    },
}


def setup_logging():
    """Configures logging using LOGGING_CONFIG, allowing overrides via environment variables."""
    config_copy = copy.deepcopy(LOGGING_CONFIG)
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # Check environment variables for overrides
    for logger_name in config_copy.get("loggers", {}):
        # Create env var name: uppercase, replace non-alpha with _, handle root logger
        env_var_logger_name = (
            logger_name.replace(".", "_") if logger_name else "ROOT"
        ).upper()
        env_var_name = f"TRON_LOG_LEVEL_{env_var_logger_name}"
        env_level = os.getenv(env_var_name)
    
        if env_level:
            level_upper = env_level.upper()
            if level_upper in valid_levels:
                config_copy["loggers"][logger_name]["level"] = level_upper
            else:
                print(
                    f"Warning: Invalid log level '{env_level}' specified in environment variable {env_var_name}. Using default."
                )

    logging.config.dictConfig(config_copy)


# --- End Logging Configuration ---

# Module-level logger for config.py
logger = logging.getLogger("tron_ai.config")
logger.info("[LOGGING TEST] tron_ai.config logger is active.")
