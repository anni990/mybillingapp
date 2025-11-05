"""
Shopkeeper blueprint package.
This module creates a modular blueprint following Flask best practices.
"""
from flask import Blueprint

# Create the blueprint
shopkeeper_bp = Blueprint('shopkeeper', __name__, url_prefix='/shopkeeper')

# Import routes - import AFTER blueprint creation to avoid circular imports
# from . import routes

# Register view modules
from .views import dashboard, bills, products, reports, customers, profile, ca_connections, purchase_bills, messages

# Register routes from each module
dashboard.register_routes(shopkeeper_bp)
bills.register_routes(shopkeeper_bp)
products.register_routes(shopkeeper_bp)
reports.register_routes(shopkeeper_bp)
customers.register_routes(shopkeeper_bp)
profile.register_routes(shopkeeper_bp)
ca_connections.register_routes(shopkeeper_bp)
purchase_bills.register_routes(shopkeeper_bp)
messages.register_routes(shopkeeper_bp)