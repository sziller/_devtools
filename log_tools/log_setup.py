"""=== Logger setup
by Sziller ==="""

import os
import logging
from logging.config import dictConfig
from time_format import TimeFormat as TiFo


def setup_logger(conf, logger_name: str = "sz_logger"):
    """ Function to setup logger =======================================================================================
    ============================================================================================== by Sziller ==="""
    log_ts = f"_{TiFo.timestamp()}" if conf.LOG_TIMED else ""
    log_fullfilename = conf.LOG_FILENAME.format(conf.LOG_PATH.format(conf.PATH_ROOT), log_ts)

    # Ensure the log directory exists
    log_dir = conf.LOG_PATH.format(conf.PATH_ROOT)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configures logging for both console and file outputs
    log_conf = {
        "version": 1,  # Indicates the schema version for the logging configuration dictionary format
        "disable_existing_loggers": False,  # Keeps any existing loggers enabled and prevents them from being disabled
        # Formatter configuration: defines the format for logged messages
        "formatters": {
            "default": {  # Named formatter, "default", that can be referenced by handlers
                "format": conf.LOG_FORMAT,  # Specifies the layout of log messages using conf.LOG_FORMAT (from config)
                "datefmt": conf.LOG_TIMEFORMAT,  # Defines the date format in log messages using conf.LOG_TIMEFORMAT
            },
        },
        # Handler configuration: sets up handlers for file and console outputs
        "handlers": {
            "file": {  # File handler configuration to write logs to a file
                "class": "logging.FileHandler",  # Uses the FileHandler class to handle file-based logging
                "filename": log_fullfilename,  # The path to the log file, defined as log_fullfilename
                "formatter": "default",  # Applies the "default" formatter to format log messages
                "level": getattr(logging, conf.LOG_LEVEL_FILE),
                "mode": "w"
                # Sets log level for file handler using conf.LOG_LEVEL_FILE
            },
            "console": {  # Console handler configuration to output logs to the terminal
                "class": "logging.StreamHandler",  # Uses StreamHandler to output logs to the console
                "formatter": "default",  # Applies the "default" formatter for console logs
                "level": getattr(logging, conf.LOG_LEVEL_CONS),  # Sets console log level using conf.LOG_LEVEL_CONS
                "stream": "ext://sys.stdout",  # Explicitly set to stdout to avoid stderr recursion
            },
        },
        # Root logger configuration: applies settings for the base/root logger
        "root": {
            "level": "DEBUG",  # Ensures that the root logger captures all logs at DEBUG level and above
            "handlers": ["file", "console"],  # Sends root logger output to both file and console handlers
        },
        # Logger configurations for specific modules
        "loggers": {
            "uvicorn": {
                "level": "INFO",
                "handlers": ["file", "console"],
                "propagate": False
            },
            "passlib": {
                "level": "WARNING",  # Set passlib to a higher level to suppress debug logs
                "handlers": ["file", "console"],
                "propagate": False
            }
        }
    }

    dictConfig(log_conf)
    return logging.getLogger(logger_name), log_conf
