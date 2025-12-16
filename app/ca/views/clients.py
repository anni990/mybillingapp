"""
Client management routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.models import (CharteredAccountant, CAConnection, Shopkeeper, User, Document)
from app.extensions import db
from app.ca.services import CAClientService


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

        # Get clients with approved or pending connection status only (exclude rejected)
        connections = CAConnection.query.filter_by(ca_id=ca.ca_id).filter(
            CAConnection.status.in_(['approved', 'pending'])
        ).all()
        clients = []
        for conn in connections:
            shop = Shopkeeper.query.get(conn.shopkeeper_id)
            if shop:
                # Get the associated user account
                user = User.query.get(shop.user_id) if shop.user_id else None
                client_data = {
                    'shopkeeper_id': shop.shopkeeper_id,
                    'shop_name': shop.shop_name,
                    'domain': shop.domain,
                    'contact_number': shop.contact_number,
                    'status': conn.status,
                    'user': user  # Include user data for credentials
                }
                clients.append(client_data)
        return render_template('ca/clients.html', clients=clients, firm_name=firm_name)
    
    @bp.route('/clients/add', methods=['GET', 'POST'])
    @login_required
    def add_client():
        """Add new client - CA managed shopkeeper profile."""
        if current_user.role != 'CA':
            flash('Access denied.', 'danger')
            return redirect(url_for('ca.dashboard'))
        
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if not ca:
            flash('CA profile not found.', 'danger')
            return redirect(url_for('ca.dashboard'))
        
        if request.method == 'POST':
            # Get form data
            client_data = {
                'shop_name': request.form.get('shop_name'),
                'email': request.form.get('email'),
                'username': request.form.get('username'),
                'password': request.form.get('password'),
                'owner_name': request.form.get('owner_name'),
                'business_type': request.form.get('business_type'),
                'business_address': request.form.get('business_address'),
                'owner_address': request.form.get('owner_address'),
                'established_year': request.form.get('established_year'),
                'pan_number': request.form.get('pan_number'),
                'gst_number': request.form.get('gst_number'),
                'contact_number': request.form.get('contact_number'),
                'city': request.form.get('city'),
                'state': request.form.get('state'),
                'pincode': request.form.get('pincode'),
                'domain': request.form.get('domain')
            }
            
            # Validate data
            is_valid, error_message = CAClientService.validate_client_data(client_data)
            if not is_valid:
                flash(error_message, 'danger')
                return render_template('ca/client_add.html', firm_name=ca.firm_name, form_data=client_data)
            
            # Create client
            shopkeeper, success = CAClientService.create_client(ca.ca_id, client_data)
            if success:
                # Get the created user to show credentials
                user = User.query.get(shopkeeper.user_id)
                flash(f'Client "{client_data["shop_name"]}" added successfully!', 'success')
                flash(f'Login credentials - Username: {user.username}, Password: {user.plain_password}', 'info')
                return redirect(url_for('ca.clients'))
            else:
                flash('Error creating client. Please try again.', 'danger')
                return render_template('ca/client_add.html', firm_name=ca.firm_name, form_data=client_data)
        
        return render_template('ca/client_add.html', firm_name=ca.firm_name)
    
    @bp.route('/clients/<int:shopkeeper_id>')
    @login_required
    def client_profile(shopkeeper_id):
        """Client profile - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if not ca:
            flash('CA profile not found', 'danger')
            return redirect(url_for('ca.clients'))
        
        shop = Shopkeeper.query.get(shopkeeper_id)
        if not shop:
            flash('Client not found', 'danger')
            return redirect(url_for('ca.clients'))
        
        # Check if the shopkeeper is connected to this CA with approved status
        connection = CAConnection.query.filter_by(
            ca_id=ca.ca_id,
            shopkeeper_id=shopkeeper_id,
            status='approved'
        ).first()
        
        if not connection:
            flash('Shopkeeper not connected yet.', 'warning')
            return redirect(url_for('ca.clients'))
        
        firm_name = ca.firm_name
        user = User.query.get(shop.user_id)  # Fetch the related user
        documents = shop.documents  # List of Document objects
        
        return render_template('ca/client_profile.html', client=shop, user=user, documents=documents, firm_name=firm_name)