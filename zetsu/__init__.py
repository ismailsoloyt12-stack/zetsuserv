import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Optional mail support
try:
    from flask_mail import Mail
    mail = Mail()
except ImportError:
    mail = None

def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Initialize mail if available
    if mail:
        mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'public.user_login'  # Default to user login
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader callback for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from zetsu.models import AdminUser, User
        # Check if it's an admin user (prefixed with 'admin_')
        if user_id.startswith('admin_'):
            return AdminUser.query.get(int(user_id.replace('admin_', '')))
        # Otherwise it's a regular user
        return User.query.get(int(user_id))
    
    # Ensure User model returns correct ID for Flask-Login
    from zetsu.models import User, AdminUser
    original_admin_get_id = AdminUser.get_id
    AdminUser.get_id = lambda self: f'admin_{self.id}'
    
    # Register blueprints
    from zetsu.routes_public import public_bp
    from zetsu.routes_admin import admin_bp
    
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    
    # Register CLI commands blueprint
    from zetsu import commands
    app.register_blueprint(commands.bp)
    
    # Import models to ensure they are registered with SQLAlchemy
    from zetsu import models
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('403.html'), 403
    
    # Add context processors
    @app.context_processor
    def inject_config():
        """Inject configuration into templates."""
        return dict(
            app_name='ZetsuServ',
            company_email='info@zetsuserv.com',
            company_phone='+1 (555) 123-4567'
        )
    
    # Template filters
    @app.template_filter('datetime')
    def datetime_filter(dt, format='%Y-%m-%d %H:%M'):
        """Format datetime objects."""
        if dt:
            return dt.strftime(format)
        return ''
    
    @app.template_filter('currency')
    def currency_filter(value):
        """Format currency values."""
        if isinstance(value, (int, float)):
            return f'${value:,.2f}'
        return value
    
    # CLI commands are defined in app.py
    
    return app