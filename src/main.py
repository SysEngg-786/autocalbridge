# File: src/main.py
# Path: /autocalbridge/src/main.py
# Purpose: Entry point for AutoCalBridge application.

import sys
import os

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.visa_manager import VisaManager
from src.utils.config_loader import load_config
from src.utils.logger import setup_logging


def main():
    """Main entry point for the application."""
    print("AutoCalBridge v0.1.0")
    print("=" * 50)
    
    # Load configuration
    config = load_config()
    print(f"Loaded configuration for {config.get('vendor', 'Unknown')} {config.get('instrument_model', 'Unknown')}")
    
    # Setup logging
    setup_logging(config.get('logging_level', 'INFO'))
    
    # Initialize VISA manager
    visa_manager = VisaManager()
    
    # Test VISA connection
    resources = visa_manager.list_resources()
    print(f"Found {len(resources)} VISA resources")
    for resource in resources:
        print(f"  - {resource}")
    
    print("=" * 50)
    print("AutoCalBridge initialization complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())