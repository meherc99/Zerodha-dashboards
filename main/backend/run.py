"""Application entry point."""
from dotenv import load_dotenv
import logging
import os

# Suppress noisy watchdog inotify debug events from site-packages monitoring
logging.getLogger('watchdog.observers.inotify_buffer').setLevel(logging.WARNING)

# Load environment variables from .env file
load_dotenv()

from app import create_app

# Create Flask app. The factory deliberately does not start worker threads.
app = create_app()

if __name__ == '__main__':
    if app.config.get('SCHEDULER_ENABLED'):
        app.scheduler.start()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.debug)
