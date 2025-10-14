"""
CA connections and marketplace routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from ..utils import shopkeeper_required
from app.models import (
    Shopkeeper, CharteredAccountant, ShopConnection, CAConnection, 
    EmployeeClient, CAEmployee
)
from app.extensions import db


def register_routes(bp):
    """Register CA connection routes to the blueprint."""
    
    @bp.route('/ca_marketplace', methods=['GET', 'POST'])
    @login_required
    @shopkeeper_required
    def ca_marketplace():
        """CA marketplace view - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        # First check if shopkeeper has any approved CA connection
        approved_connection = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='approved'
        ).first()
        
        # If there's an approved connection, only get that CA's details
        if approved_connection:
            connected_ca = CharteredAccountant.query.get(approved_connection.ca_id)
            cas = [connected_ca] if connected_ca else []
        else:
            # If no approved connection, show all CAs
            cas = []
            if request.method == 'POST':
                area = request.form.get('area')
                domain = request.form.get('domain')
                query = CharteredAccountant.query
                if area:
                    query = query.filter(CharteredAccountant.area.ilike(f'%{area}%'))
                cas = query.all()
            else:
                cas = CharteredAccountant.query.all()
        
        # Get connection status for each CA
        connections = {c.ca_id: c for c in ShopConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()}
        
        return render_template('shopkeeper/ca_marketplace.html', 
                             cas=cas, 
                             connections=connections,
                             has_approved_connection=bool(approved_connection))
    
    @bp.route('/ca_profile/<int:ca_id>')
    @login_required
    @shopkeeper_required
    def ca_profile(ca_id):
        """View CA profile - preserves original logic."""
        ca = CharteredAccountant.query.get_or_404(ca_id)
        return render_template('shopkeeper/ca_profile.html', ca=ca)
    
    @bp.route('/request_connection/<int:ca_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def request_connection(ca_id):
        """Request connection to a CA - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        ca = CharteredAccountant.query.get_or_404(ca_id)

        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Check if already connected
        existing_connection = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id
        ).first()

        if existing_connection:
            message = 'You are already connected to this CA.'
            if is_ajax:
                return jsonify({'success': False, 'message': message})
            flash(message, 'info')
            return redirect(url_for('shopkeeper.ca_marketplace'))

        # Check if request already sent
        existing_request = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id
        ).first()

        if existing_request:
            message = 'Connection request already sent to this CA.'
            if is_ajax:
                return jsonify({'success': False, 'message': message})
            flash(message, 'info')
            return redirect(url_for('shopkeeper.ca_marketplace'))

        # Create connection request
        shop_connection = ShopConnection(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id,
            status='pending'
        )

        db.session.add(shop_connection)
        db.session.commit()

        message = 'Connection request sent successfully!'
        if is_ajax:
            return jsonify({'success': True, 'message': message})
        
        flash(message, 'success')
        return redirect(url_for('shopkeeper.ca_marketplace'))
    
    @bp.route('/my_cas')
    @login_required
    @shopkeeper_required
    def my_cas():
        """View connected CAs - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        # Get connected CAs
        ca_connections = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).all()
        
        connected_cas = []
        for connection in ca_connections:
            ca = CharteredAccountant.query.get(connection.ca_id)
            if ca:
                connected_cas.append({
                    'ca': ca,
                    'connection_date': connection.connection_date
                })
        
        # Get pending requests
        pending_requests = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='pending'
        ).all()
        
        pending_cas = []
        for request in pending_requests:
            ca = CharteredAccountant.query.get(request.ca_id)
            if ca:
                pending_cas.append({
                    'ca': ca,
                    'request_date': request.request_date
                })
        
        return render_template(
            'shopkeeper/my_cas.html',
            connected_cas=connected_cas,
            pending_cas=pending_cas
        )
    
    @bp.route('/disconnect_ca/<int:ca_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def disconnect_ca(ca_id):
        """Disconnect from a CA - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        # Remove CA connection
        ca_connection = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id
        ).first()
        
        if ca_connection:
            db.session.delete(ca_connection)
        
        # Remove employee connections if any
        employee_connections = EmployeeClient.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).all()
        
        for emp_conn in employee_connections:
            employee = CAEmployee.query.get(emp_conn.employee_id)
            if employee and employee.ca_id == ca_id:
                db.session.delete(emp_conn)
        
        db.session.commit()
        flash('Successfully disconnected from CA.', 'success')
        return redirect(url_for('shopkeeper.my_cas'))
    
    @bp.route('/cancel_request/<int:ca_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def cancel_request(ca_id):
        """Cancel connection request - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        shop_connection = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id,
            status='pending'
        ).first()
        
        if shop_connection:
            db.session.delete(shop_connection)
            db.session.commit()
            flash('Connection request cancelled.', 'success')
        else:
            flash('Request not found.', 'error')
        
        return redirect(url_for('shopkeeper.my_cas'))
    
    
    @bp.route('/ca/profile/<int:ca_id>')
    @login_required
    @shopkeeper_required
    def connected_ca_profile(ca_id):
        """View connected CA profile - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        # Verify connection exists
        ca_conn = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id,
            status='approved'
        ).first()
        
        if not ca_conn:
            flash('No connection found with this CA.', 'danger')
            return redirect(url_for('shopkeeper.dashboard'))
        
        # Get CA details
        ca = CharteredAccountant.query.get_or_404(ca_id)
        
        # Get assigned employees
        assigned_employees = db.session.query(CAEmployee)\
            .join(EmployeeClient, CAEmployee.employee_id == EmployeeClient.employee_id)\
            .filter(EmployeeClient.shopkeeper_id == shopkeeper.shopkeeper_id)\
            .all()
        
        return render_template('shopkeeper/connected_ca_profile.html',
            ca=ca,
            assigned_employees=assigned_employees
        )
    
    @bp.route('/search_cas')
    @login_required
    @shopkeeper_required
    def search_cas():
        """Search CAs - preserves original logic."""
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify([])
        
        cas = CharteredAccountant.query.filter(
            CharteredAccountant.ca_name.ilike(f'%{query}%') |
            CharteredAccountant.specialization.ilike(f'%{query}%') |
            CharteredAccountant.city.ilike(f'%{query}%')
        ).limit(10).all()
        
        results = []
        for ca in cas:
            results.append({
                'id': ca.ca_id,
                'name': ca.ca_name,
                'specialization': ca.specialization,
                'city': ca.city,
                'rating': float(ca.rating) if ca.rating else 0,
                'experience': ca.experience_years
            })
        
        return jsonify(results)