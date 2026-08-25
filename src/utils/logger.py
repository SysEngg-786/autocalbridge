# File: src/utils/logger.py
# Path: /autocalbridge/src/utils/logger.py
# Purpose: Logging setup for the application.

import logging
import os
from datetime import datetime


def setup_logging(level="INFO"):
    """Configure logging to both console and file."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"autocalbridge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logging.info(f"Logging initialized. Log file: {log_file}")