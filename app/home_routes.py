from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from app.auth.utils import redirect_to_dashboard

home_bp = Blueprint('home', __name__, url_prefix='/')

@home_bp.route('/')
def index():
    # Always show the home page - users can visit it whether logged in or not
    return render_template('home/index.html')

@home_bp.route('/login')
def login_redirect():
    """
    Handle general /login URL access.
    If user is already logged in, redirect to dashboard.
    If not, redirect to proper login page.
    """
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    else:
        return redirect(url_for('auth.login'))

@home_bp.route('/dashboard')
def dashboard_redirect():
    """
    Handle general /dashboard URL access.
    Redirect based on user's role or to login if not authenticated.
    """
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    else:
        return redirect(url_for('auth.login'))

@home_bp.route('/mobile-view')
def mobile_view():
    """
    Mobile-optimized app view.
    Shows mobile-first interface designed for web-to-app conversion.
    """
    return render_template('mobile/mobile_view.html')

@home_bp.route('/features')
def features():
    return render_template('home/features.html')

@home_bp.route('/pricing')
def pricing():
    return render_template('home/pricing.html')

@home_bp.route('/about')
def about():
    return render_template('home/about.html')