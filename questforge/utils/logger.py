import logging

# This utility is now simplified. Configuration should happen centrally,
# typically during Flask app initialization.

def get_logger(name):
    """Retrieves a logger instance."""
    # Basic configuration in case central setup hasn't run (e.g., during tests or standalone scripts)
    # This won't interfere with central configuration if it has already run.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(name)
