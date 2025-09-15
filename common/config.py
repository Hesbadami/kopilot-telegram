from dotenv import load_dotenv
from pathlib import Path
import os
import logging
import logging.config
import logging.handlers

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

MYSQL_CFG = {
    'host': os.environ.get("MYSQL_HOST"),
    'user': os.environ.get("MYSQL_USER"),
    'password': os.environ.get("MYSQL_PASSWORD"),
    'database': os.environ.get("MYSQL_DATABASE"),
    'pool_size': 5,
}

TELEGRAM_SECRET = os.environ.get("TELEGRAM_SECRET")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

MEDIA_PATH = os.environ.get("MEDIA_PATH")

NATS_CFG = {
    'servers': os.environ.get("NATS_URL"),
    'name': 'kopilot_telegram',
    'reconnect_time_wait': 2,
    'max_reconnect_attempts': 10
}

LOGGING_CFG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(process)d %(thread)d %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'main_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get("LOG_PATH")+"main.log",
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
        },
        'mysql_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get("LOG_PATH")+"mysql.log",
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
        },
        'telegram_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get("LOG_PATH")+"telegram.log",
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
        },
        'nats_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.environ.get("LOG_PATH")+"nats.log",
            'formatter': 'verbose',
            'encoding': 'utf-8',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'main_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'mysql': {
            'handlers': ['console', 'mysql_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'telegram': {
            'handlers': ['console', 'telegram_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'nats': {
            'handlers': ['console', 'nats_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

logging.config.dictConfig(LOGGING_CFG)