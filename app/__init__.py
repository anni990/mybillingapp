from flask import Flask, redirect, url_for
from .config import Config
from .extensions import db, login_manager, bcrypt, session

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    session.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Set up automatic redirection for authenticated users trying to access auth pages
    @app.before_request
    def handle_authentication_redirection():
        from flask import request
        from flask_login import current_user
        from .auth.utils import redirect_to_dashboard
        
        # Skip API endpoints and static files
        if (request.endpoint and 
            (request.endpoint.startswith('api.') or 
             request.endpoint.startswith('walkthrough.') or
             request.endpoint.startswith('preview.') or
             request.endpoint == 'static')):
            return None
        
        # Only redirect authenticated users away from auth-specific pages
        # Allow them to visit home page, features, pricing, etc.
        auth_only_endpoints = ['auth.login', 'auth.register', 'auth.auth_root']
        
        if (current_user.is_authenticated and 
            request.endpoint in auth_only_endpoints):
            return redirect_to_dashboard()
        
        return None
    
    # Import and register blueprints
    from .auth.routes import auth_bp
    from .shopkeeper import shopkeeper_bp 
    from .ca import ca_bp
    from .api.routes import api_bp
    from .api.walkthrough_routes import walkthrough_bp
    from .api.gst_preview import preview_bp
    from .home_routes import home_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shopkeeper_bp)
    app.register_blueprint(ca_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(walkthrough_bp)
    app.register_blueprint(preview_bp)
    app.register_blueprint(home_bp)

    # Context processor to make user info available in templates
    @app.context_processor
    def inject_user_info():
        from flask_login import current_user
        from .auth.utils import get_dashboard_url_for_role
        
        user_info = {
            'current_user': current_user,
            'is_authenticated': current_user.is_authenticated,
            'user_role': getattr(current_user, 'role', None) if current_user.is_authenticated else None,
        }
        
        # Add dashboard URL for the user's role
        if current_user.is_authenticated:
            user_info['dashboard_url'] = get_dashboard_url_for_role(current_user.role)
        
        return user_info

    # Custom template filters
    @app.template_filter('format_bill_date')
    def format_bill_date(bill_date, date_with_time=True):
        """Format bill date based on date_with_time setting."""
        if not bill_date:
            return ''
        
        if date_with_time:
            # Show date with time: dd-mm-yyyy hh:mm:ss
            return bill_date.strftime('%d-%m-%Y %H:%M:%S')
        else:
            # Show date only: dd-mm-yyyy
            return bill_date.strftime('%d-%m-%Y')
    
    @app.template_filter('from_json')
    def from_json(json_str):
        """Convert JSON string to Python object."""
        if not json_str:
            return []
        try:
            import json
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return []

    # Error handlers
    @app.errorhandler(401)
    def unauthorized_access(error):
        from flask import flash, redirect, url_for
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login'))

    @app.errorhandler(403)
    def forbidden_access(error):
        from flask import flash
        from flask_login import current_user
        from .auth.utils import redirect_to_dashboard
        
        if current_user.is_authenticated:
            flash('Access denied. You do not have permission to access this page.', 'danger')
            return redirect_to_dashboard()
        else:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

    return app
