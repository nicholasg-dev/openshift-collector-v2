from flask import Flask
from config import Config

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.config.from_pyfile('config.py', silent=True)  # Load instance config if it exists

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Register scheduler and its API endpoints within app context
    from app.scheduler import init_app as init_scheduler
    with app.app_context():
        init_scheduler(app)

    @app.route('/health')
    def health_check():
        """Simple health check endpoint."""
        return {'status': 'healthy'}

    return app
