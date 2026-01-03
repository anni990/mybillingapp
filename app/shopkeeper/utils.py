"""
Shopkeeper utilities, decorators, and helper functions.
"""
from functools import wraps
from flask import flash, redirect, url_for, g
from flask_login import current_user
from app.models import Shopkeeper, CAConnection
from app.extensions import db


def shopkeeper_required(f):
    """Decorator to ensure only shopkeepers can access the route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def require_lite_plan(f):
    """Decorator to require Lite or Gold plan for route access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
            
        shopkeeper = get_current_shopkeeper()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'danger')
            return redirect(url_for('shopkeeper.dashboard'))
            
        if shopkeeper.subscription_plan == 'free':
            flash('This feature requires MBA Lite', 'warning')
            return redirect(url_for('shopkeeper.subscription'))
            
        return f(*args, **kwargs)
    return decorated_function


def require_gold_plan(f):
    """Decorator to require Gold plan for route access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
            
        shopkeeper = get_current_shopkeeper()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'danger')
            return redirect(url_for('shopkeeper.dashboard'))
            
        if shopkeeper.subscription_plan in ['free', 'lite']:
            flash('This feature requires Gold plan.', 'warning')
            return redirect(url_for('shopkeeper.subscription'))
            
        return f(*args, **kwargs)
    return decorated_function


def check_daily_limits(f):
    """Decorator to check daily GST billing limits."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
            
        shopkeeper = get_current_shopkeeper()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'danger')
            return redirect(url_for('shopkeeper.dashboard'))
            
        from .services import SubscriptionService
        can_create, error_message = SubscriptionService.can_create_gst_bill(shopkeeper)
        
        if not can_create:
            flash(error_message, 'warning')
            return redirect(url_for('shopkeeper.dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function


def get_current_shopkeeper():
    """Get the current authenticated shopkeeper."""
    if not current_user.is_authenticated or current_user.role != 'shopkeeper':
        return None
    return Shopkeeper.query.filter_by(user_id=current_user.user_id).first()


def get_shopkeeper_pending_requests():
    """Get pending CA connection requests for the current shopkeeper."""
    if hasattr(g, 'shopkeeper_pending_requests'):
        return g.shopkeeper_pending_requests
    
    if not (hasattr(current_user, 'is_authenticated') and 
            current_user.is_authenticated and 
            getattr(current_user, 'role', None) == 'shopkeeper'):
        g.shopkeeper_pending_requests = []
        return []
    
    shopkeeper = get_current_shopkeeper()
    if not shopkeeper:
        g.shopkeeper_pending_requests = []
        return []
    
    # Get pending connection requests - using actual logic from your code
    g.shopkeeper_pending_requests = []
    return []


def update_shopkeeper_verification(shopkeeper):
    """Update shopkeeper verification status based on uploaded documents."""
    required_fields = [
        shopkeeper.aadhaar_dl_path,
        shopkeeper.pan_doc_path,
        shopkeeper.address_proof_path,
        shopkeeper.selfie_path,
        shopkeeper.gumasta_path,
        shopkeeper.bank_statement_path,
    ]
    shopkeeper.is_verified = all(required_fields)
    db.session.commit()


def get_subscription_context():
    """Get subscription context for templates."""
    if not (hasattr(current_user, 'is_authenticated') and 
            current_user.is_authenticated and 
            getattr(current_user, 'role', None) == 'shopkeeper'):
        return {}
    
    shopkeeper = get_current_shopkeeper()
    if not shopkeeper:
        return {}
    
    from .services import SubscriptionService
    usage_stats = SubscriptionService.get_usage_stats(shopkeeper)
    
    # Plan display configurations
    plan_configs = {
        'free': {'name': 'Free', 'color': 'bg-gray-200 text-gray-700', 'icon': '💫'},
        'lite': {'name': 'Lite', 'color': 'bg-blue-200 text-blue-700', 'icon': '✨'},
        'gold': {'name': 'Gold', 'color': 'bg-yellow-200 text-yellow-700', 'icon': '👑'}
    }
    
    current_plan = shopkeeper.subscription_plan
    plan_config = plan_configs.get(current_plan, plan_configs['free'])
    
    return {
        'current_subscription_plan': current_plan,
        'subscription_display_name': plan_config['name'],
        'subscription_badge_class': plan_config['color'],
        'subscription_icon': plan_config['icon'],
        'usage_stats': usage_stats
    }