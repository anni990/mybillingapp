"""
Connections and marketplace routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app.models import (CharteredAccountant, CAConnection, ShopConnection, Shopkeeper)
from app.extensions import db


def register_routes(bp):
    """Register connections and marketplace routes to the blueprint."""
    
    @bp.route('/connection_requests', methods=['GET', 'POST'])
    @login_required
    def connection_requests():
        """Connection requests - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if request.method == 'POST':
            conn_id = request.form.get('conn_id')
            action = request.form.get('action')
            conn = CAConnection.query.get(conn_id)
            if conn and conn.ca_id == ca.ca_id and conn.status == 'pending':
                if action == 'accept':
                    conn.status = 'approved'
                    db.session.commit()
                    flash('Connection approved.', 'success')
                elif action == 'reject':
                    conn.status = 'rejected'
                    db.session.commit()
                    flash('Connection rejected.', 'info')
            return redirect(url_for('ca.connection_requests'))
        # GET: show pending requests
        pending = CAConnection.query.filter_by(ca_id=ca.ca_id, status='pending').all()
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
        return render_template('ca/connection_requests.html', requests=requests)

    @bp.route('/shopkeeper_marketplace', methods=['GET', 'POST'])
    @login_required
    def shopkeeper_marketplace():
        """Shopkeeper marketplace - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name
        shopkeepers = []
        if request.method == 'POST':
            area = request.form.get('area')
            domain = request.form.get('domain')
            query = Shopkeeper.query
            if area:
                query = query.filter(Shopkeeper.address.ilike(f'%{area}%'))
            if domain:
                query = query.filter(Shopkeeper.domain.ilike(f'%{domain}%'))
            shopkeepers = query.all()
        else:
            shopkeepers = Shopkeeper.query.all()
        # Get connection status for each shopkeeper
        connections = {c.shopkeeper_id: c for c in CAConnection.query.filter_by(ca_id=ca.ca_id).all()}
        return render_template('ca/shopkeeper_marketplace.html', shopkeepers=shopkeepers, connections=connections, firm_name=firm_name)

    @bp.route('/connect_shopkeeper/<int:shopkeeper_id>', methods=['POST'])
    @login_required
    def connect_shopkeeper(shopkeeper_id):
        """Connect to shopkeeper - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        existing = CAConnection.query.filter_by(shopkeeper_id=shopkeeper_id, ca_id=ca.ca_id).first()
        if not existing:
            conn = CAConnection(shopkeeper_id=shopkeeper_id, ca_id=ca.ca_id, status='pending')
            db.session.add(conn)
            db.session.commit()
            flash('Connection request sent.', 'success')
        else:
            if existing.status == 'pending':
                flash('Request already sent and pending approval.', 'info')
            elif existing.status == 'approved':
                flash('You are already connected with this shopkeeper.', 'info')
            elif existing.status == 'rejected':
                # Allow resending if rejected
                existing.status = 'pending'
                db.session.commit()
                flash('Connection request resent.', 'success')
        return redirect(url_for('ca.shopkeeper_marketplace'))

    @bp.route('/handle_shop_connection_request', methods=['POST'])
    @login_required
    def handle_shop_connection_request():
        """Handle shop connection request - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        conn_id = request.form.get('conn_id')
        action = request.form.get('action')
        conn = ShopConnection.query.get(conn_id)
        if conn and conn.ca_id == ca.ca_id and conn.status == 'pending':
            # Find or create the corresponding CAConnection
            ca_conn = CAConnection.query.filter_by(shopkeeper_id=conn.shopkeeper_id, ca_id=ca.ca_id).first()
            if not ca_conn:
                ca_conn = CAConnection(shopkeeper_id=conn.shopkeeper_id, ca_id=ca.ca_id, status='pending')
                db.session.add(ca_conn)
            if action == 'accept':
                conn.status = 'approved'
                ca_conn.status = 'approved'
                db.session.commit()
                flash('Connection approved.', 'success')
            elif action == 'reject':
                conn.status = 'rejected'
                ca_conn.status = 'rejected'
                db.session.commit()
                flash('Connection rejected.', 'info')
        return redirect(request.referrer or url_for('ca.dashboard'))