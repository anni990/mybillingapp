"""
Messages management routes for Shopkeeper.
Handles the messaging interface with connected CA.
"""
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from app.models import Shopkeeper, CAConnection, CharteredAccountant, Message, Bill
from app.extensions import db

def register_routes(bp):
    """Register messages routes to the blueprint."""
    
    @bp.route('/messages')
    @login_required
    def messages():
        """Messages page for Shopkeeper - chat interface with connected CA."""
        if current_user.role != 'shopkeeper':
            flash('Access denied: Only shopkeepers can access messages.', 'danger')
            return redirect(url_for('auth.login'))
        
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            flash('Error: Shopkeeper profile not found.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Get connected CA
        connection = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='approved'
        ).first()
        
        connected_ca = None
        if connection:
            connected_ca = CharteredAccountant.query.get(connection.ca_id)
        
        return render_template('shopkeeper/messages.html', 
                             shopkeeper=shopkeeper,
                             connected_ca=connected_ca,
                             current_user=current_user)
    
    @bp.route('/bills/<int:bill_id>/remark', methods=['POST'])
    @login_required
    def add_bill_remark(bill_id):
        """Add a remark to a specific bill (shopkeeper to CA)."""
        if current_user.role != 'shopkeeper':
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            data = request.get_json()
            remark_text = data.get('remark_text', '').strip()
            
            if not remark_text:
                return jsonify({'error': 'Remark text is required'}), 400
            
            if len(remark_text) > 2000:
                return jsonify({'error': 'Remark too long (max 2000 characters)'}), 400
            
            # Get the bill
            bill = Bill.query.get(bill_id)
            if not bill:
                return jsonify({'error': 'Bill not found'}), 404
            
            # Verify shopkeeper owns this bill
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper or bill.shopkeeper_id != shopkeeper.shopkeeper_id:
                return jsonify({'error': 'Access denied to this bill'}), 403
            
            # Check connection to CA
            connection = CAConnection.query.filter_by(
                shopkeeper_id=shopkeeper.shopkeeper_id,
                status='approved'
            ).first()
            
            if not connection:
                return jsonify({'error': 'No CA connection found'}), 403
            
            ca = CharteredAccountant.query.get(connection.ca_id)
            if not ca:
                return jsonify({'error': 'Connected CA not found'}), 404
            
            # Create remark message
            message = Message(
                sender_id=str(current_user.user_id),
                receiver_id=str(ca.user.user_id),
                message=remark_text,
                message_type='remark',
                bill_id=bill_id
            )
            
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message_id': message.id,
                'timestamp': message.timestamp.isoformat() + 'Z'
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Internal server error'}), 500