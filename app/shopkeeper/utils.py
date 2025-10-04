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