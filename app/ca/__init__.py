"""
CA blueprint package.
This module creates a modular blueprint following Flask best practices.
"""
from flask import Blueprint

from .utils import get_ca_pending_requests

# Create the blueprint
ca_bp = Blueprint('ca', __name__, url_prefix='/ca')

@ca_bp.app_context_processor
def inject_ca_pending_requests():
    """Inject CA pending requests - preserves original logic."""
    return {'ca_pending_requests': get_ca_pending_requests()}

# Register view modules
from .views import dashboard, employee_dashboard, clients, employees, bills, connections, reports

# Register routes from each module
dashboard.register_routes(ca_bp)
employee_dashboard.register_routes(ca_bp)
clients.register_routes(ca_bp)
employees.register_routes(ca_bp)
bills.register_routes(ca_bp)
connections.register_routes(ca_bp)
reports.register_routes(ca_bp)