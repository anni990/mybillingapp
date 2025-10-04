"""
Utilities for CA blueprint.
Contains shared functions and context processors.
"""
from flask import g
from flask_login import current_user

from app.models import CharteredAccountant, ShopConnection, Shopkeeper


def get_ca_pending_requests():
    """Get pending CA requests - preserves original logic."""
    if hasattr(g, 'ca_pending_requests'):
        return g.ca_pending_requests
    
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and getattr(current_user, 'role', None) == 'CA':
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if ca:
            pending = ShopConnection.query.filter_by(ca_id=ca.ca_id, status='pending').all()
            requests = []
            for conn in pending:
                shop = Shopkeeper.query.get(conn.shopkeeper_id)
                requests.append({
                    'conn_id': conn.id,
                    'shopkeeper_id': shop.shopkeeper_id,
                    'shop_name': shop.shop_name,
                    'domain': shop.domain,
                    'contact_number': shop.contact_number
                })
            g.ca_pending_requests = requests
            return requests
    g.ca_pending_requests = []
    return []