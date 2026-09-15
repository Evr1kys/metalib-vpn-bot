"""
Structured logging configuration
"""
import sys
import json
import logging
from datetime import datetime
from typing import Any, Dict
from loguru import logger
from app.core.config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging and redirect to loguru
    """
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def serialize_json(record: Dict[str, Any]) -> str:
    """
    Custom JSON serializer for log records
    """
    subset = {
        "timestamp": record["time"].timestamp(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add extra fields
    if record["extra"]:
        subset["extra"] = record["extra"]
    
    # Add exception info
    if record["exception"]:
        subset["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
        }
    
    return json.dumps(subset)


def setup_logging() -> None:
    """
    Configure logging for the application
    """
    # Remove default logger
    logger.remove()
    
    # Define log format based on settings
    # Force text format for now to fix logging error
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )
    
    # Add file handler if configured
    if settings.log_file:
        logger.add(
            settings.log_file,
            rotation="1 day",
            retention="7 days",
            compression="gz",
            level=settings.log_level,
            format=log_format,
        )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set log levels for third-party libraries
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    logger.info(f"Logging configured: level={settings.log_level}, format={settings.log_format}")


# Export logger instance
__all__ = ["logger", "setup_logging"]
