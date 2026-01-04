from flask import Flask, redirect, url_for
from flask_wtf.csrf import generate_csrf
from .config import Config
from .extensions import db, login_manager, bcrypt, session, csrf

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    session.init_app(app)
    
    # Configure CSRF protection globally with enterprise settings
    csrf.init_app(app)
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour token validity
    app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow HTTP for development
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True  # Enable by default
    
    # Global CSRF error handler for enterprise-level error management
    @app.errorhandler(400)
    def handle_csrf_error(e):
        """Global CSRF error handler for all requests."""
        from flask import request, jsonify, render_template
        from flask_wtf.csrf import CSRFError
        
        # Check if this is specifically a CSRF error
        if isinstance(e.description, CSRFError) or 'CSRF' in str(e.description):
            if request.is_json or request.path.startswith('/api/'):
                # Return JSON response for API calls
                return jsonify({
                    'success': False,
                    'error': 'CSRF token missing or invalid',
                    'message': 'Security token expired. Please refresh the page and try again.',
                    'csrf_error': True
                }), 400
            else:
                # Return HTML response for form submissions
                return render_template('errors/csrf_error.html', 
                                     message='Security token expired. Please refresh the page and try again.'), 400
        else:
            # Handle other 400 errors normally
            return e
    
    # Specific CSRF error handler (more reliable)
    from flask_wtf.csrf import CSRFError
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Handle CSRF errors specifically."""
        from flask import request, jsonify, render_template
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'CSRF token missing or invalid',
                'message': 'Security token expired. Please refresh the page and try again.',
                'csrf_error': True
            }), 400
        else:
            return render_template('errors/csrf_error.html', 
                                 message='Security token expired. Please refresh the page and try again.'), 400
    
    # Global template context processor to inject CSRF token
    @app.context_processor
    def inject_csrf_token():
        """Inject CSRF token into all templates globally."""
        return dict(csrf_token=generate_csrf)

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
    from .auth.routes import auth_bp, init_oauth
    from .shopkeeper import shopkeeper_bp 
    from .ca import ca_bp
    from .api.routes import api_bp
    from .api.walkthrough_routes import walkthrough_bp
    from .api.gst_preview import preview_bp
    from .home_routes import home_bp

    # Initialize OAuth
    init_oauth(app)

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

    # Context processor to make CSRF token available in templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

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
