from flask import Flask, render_template
from flask_login import LoginManager
import os
from loguru import logger

from src.config import config
from src.dashboard.routes import dashboard
from src.dashboard.auth import auth, login_manager, User

def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-development-only')
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # Initialize login manager
    login_manager.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    
    # Context processor to make variables available to all templates
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    return app

def run_dashboard():
    """
    Run the dashboard application.
    """
    app = create_app()
    host = config.DASHBOARD_HOST
    port = config.DASHBOARD_PORT
    
    # Get certificate paths
    cert_path = os.path.join(os.getcwd(), 'certificates/dashboard.crt')
    key_path = os.path.join(os.getcwd(), 'certificates/dashboard.key')
    
    # Check if certificates exist
    use_ssl = os.path.exists(cert_path) and os.path.exists(key_path)
    
    if use_ssl:
        logger.info(f"Starting dashboard with HTTPS on {host}:{port}")
        app.run(host=host, port=port, debug=True, ssl_context=(cert_path, key_path))
    else:
        logger.warning(f"SSL certificates not found, starting dashboard without HTTPS on {host}:{port}")
        logger.warning(f"Expected certificates at {cert_path} and {key_path}")
        app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    run_dashboard()
