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
    
    # Import and register blueprints
    from .auth.routes import auth_bp
    from .shopkeeper.routes import shopkeeper_bp
    from .ca.routes import ca_bp
    from .api.routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shopkeeper_bp)
    app.register_blueprint(ca_bp)
    app.register_blueprint(api_bp)

    # Blank route renders the homepage
    @app.route('/')
    def index():
        from flask import render_template
        return render_template('home/index.html')

    return app
