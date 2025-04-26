"""
Application entry point.
Run this file to start the Flask development server or to be used by a WSGI server.
"""

import os
from app import create_app
from config import DevelopmentConfig, ProductionConfig

# Determine which configuration to use based on environment
if os.environ.get('FLASK_ENV') == 'production':
    app = create_app(ProductionConfig)
else:
    app = create_app(DevelopmentConfig)

if __name__ == '__main__':
    # When running directly, use development settings
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=os.environ.get('FLASK_ENV') != 'production', host='0.0.0.0', port=port)
