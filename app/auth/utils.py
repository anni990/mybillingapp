"""
Authentication utilities for role-based redirection and access control.
"""
from flask import redirect, url_for, flash
from flask_login import current_user
from functools import wraps

def get_dashboard_url_for_role(role):
    """Get the appropriate dashboard URL for a given role."""
    role_dashboard_map = {
        'shopkeeper': 'shopkeeper.dashboard',
        'CA': 'ca.dashboard',
        'employee': 'ca.employee_dashboard'
    }
    return role_dashboard_map.get(role, 'auth.login')

def redirect_to_dashboard():
    """Redirect user to their appropriate dashboard based on role."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    dashboard_route = get_dashboard_url_for_role(current_user.role)
    return redirect(url_for(dashboard_route))

def check_user_access_and_redirect():
    """
    Check if user is logged in and redirect appropriately.
    Returns None if user should continue to current page, 
    or a redirect response if they should be redirected.
    """
    if current_user.is_authenticated:
        # User is logged in, redirect to their dashboard
        return redirect_to_dashboard()
    
    # User is not logged in, let them continue (will see login page)
    return None

def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific roles.
    Usage: @role_required('CA', 'employee')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in allowed_roles:
                flash('Access denied. You do not have permission to access this page.', 'danger')
                return redirect_to_dashboard()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def ca_required(f):
    """Decorator to ensure only CAs can access the route."""
    return role_required('CA')(f)

def ca_or_employee_required(f):
    """Decorator to ensure only CAs or employees can access the route."""
    return role_required('CA', 'employee')(f)