"""
Messages management routes for CA.
Handles the messaging interface between CAs and Shopkeepers.
"""
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from app.models import CharteredAccountant, CAConnection, Message, Bill
from app.extensions import db

def register_routes(bp):
    """Register messages routes to the blueprint."""
    
    @bp.route('/messages')
    @login_required
    def messages():
        """Messages page for CA - WhatsApp-style interface."""
        if current_user.role != 'CA':
            flash('Access denied: Only CAs can access messages.', 'danger')
            return redirect(url_for('auth.login'))
        
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name if ca else 'CA'
        
        if not ca:
            flash('Error: CA profile not found.', 'danger')
            return redirect(url_for('auth.login'))
        
        return render_template('ca/messages.html', 
                             ca=ca,
                             firm_name=firm_name,
                             current_user=current_user)
    
    @bp.route('/bills/<int:bill_id>/remark', methods=['POST'])
    @login_required
    def add_bill_remark(bill_id):
        """Add a remark to a specific bill."""
        if current_user.role != 'CA':
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
            
            # Verify CA has access to this bill
            ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
            if not ca:
                return jsonify({'error': 'CA profile not found'}), 404
            
            # Check connection to shopkeeper
            connection = CAConnection.query.filter_by(
                ca_id=ca.ca_id,
                shopkeeper_id=bill.shopkeeper_id,
                status='approved'
            ).first()
            
            if not connection:
                return jsonify({'error': 'No connection to this shopkeeper'}), 403
            
            # Create remark message
            message = Message(
                sender_id=str(current_user.user_id),
                receiver_id=str(bill.shopkeeper.user.user_id),
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