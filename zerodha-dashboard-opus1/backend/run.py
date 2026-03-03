"""
Application entry point.
"""
from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create Flask app
app = create_app()

if __name__ == '__main__':
    # Run development server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
