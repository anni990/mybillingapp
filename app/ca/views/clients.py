"""
Client management routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.models import (CharteredAccountant, CAConnection, Shopkeeper, User, Document)
from app.extensions import db


def register_routes(bp):
    """Register client management routes to the blueprint."""
    
    @bp.route('/clients')
    @login_required
    def clients():
        """Client list - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name

        # Get all clients with their connection status
        connections = CAConnection.query.filter_by(ca_id=ca.ca_id).all()
        clients = []
        for conn in connections:
            shop = Shopkeeper.query.get(conn.shopkeeper_id)
            if shop:
                clients.append({
                    'shopkeeper_id': shop.shopkeeper_id,
                    'shop_name': shop.shop_name,
                    'domain': shop.domain,
                    'contact_number': shop.contact_number,
                    'status': conn.status
                })
        return render_template('ca/clients.html', clients=clients, firm_name=firm_name)
    
    @bp.route('/clients/<int:shopkeeper_id>')
    @login_required
    def client_profile(shopkeeper_id):
        """Client profile - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        shop = Shopkeeper.query.get(shopkeeper_id)
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name
        if not shop:
            flash('Client not found', 'danger')
            return redirect(url_for('ca.clients'))
        user = User.query.get(shop.user_id)  # Fetch the related user
        documents = shop.documents  # List of Document objects
        
        return render_template('ca/client_profile.html', client=shop, user=user, documents=documents, firm_name=firm_name)