"""
Messages API endpoints for CA-Shopkeeper communication.
Handles chat messages and bill remarks.
"""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import or_, and_, desc

from app.models import Message, User, CharteredAccountant, Shopkeeper, CAConnection, Bill
from app.extensions import db

def register_routes(bp):
    """Register message API routes to the blueprint."""
    
    @bp.route('/messages/send', methods=['POST'])
    @login_required
    def send_message():
        """Send a chat message or bill remark."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Validate required fields
            receiver_id = data.get('receiver_id')
            message_text = data.get('message', '').strip()
            message_type = data.get('message_type', 'chat')
            bill_id = data.get('bill_id')
            
            if not receiver_id or not message_text:
                return jsonify({'error': 'receiver_id and message are required'}), 400
            
            if len(message_text) > 2000:
                return jsonify({'error': 'Message too long (max 2000 characters)'}), 400
            
            if message_type not in ['chat', 'remark']:
                return jsonify({'error': 'Invalid message_type. Must be chat or remark'}), 400
            
            # Verify receiver exists
            receiver = User.query.filter_by(user_id=receiver_id).first()
            if not receiver:
                return jsonify({'error': 'Receiver not found'}), 404
            
            # Check if sender and receiver are connected (CA-Shopkeeper relationship)
            if not _are_users_connected(current_user.user_id, receiver_id):
                return jsonify({'error': 'Users are not connected'}), 403
            
            # If bill_id provided, verify it exists and user has access
            if bill_id:
                bill = Bill.query.get(bill_id)
                if not bill:
                    return jsonify({'error': 'Bill not found'}), 404
                
                # Check if current user can access this bill
                if not _can_access_bill(current_user.user_id, bill):
                    return jsonify({'error': 'Access denied to this bill'}), 403
            
            # Create message
            message = Message(
                sender_id=str(current_user.user_id),
                receiver_id=str(receiver_id),
                message=message_text,
                message_type=message_type,
                bill_id=bill_id,
                timestamp=datetime.utcnow()
            )
            
            db.session.add(message)
            db.session.commit()
            
            return jsonify({
                'status': 'sent',
                'id': message.id,
                'timestamp': message.timestamp.isoformat() + 'Z'
            }), 201
            
        except Exception as e:
            current_app.logger.error(f"Error sending message: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Internal server error'}), 500
    
    @bp.route('/messages/conversation/<int:partner_id>')
    @login_required
    def get_conversation(partner_id):
        """Get conversation between current user and partner."""
        try:
            # Validate partner exists
            partner = User.query.get(partner_id)
            if not partner:
                return jsonify({'error': 'Partner not found'}), 404
            
            # Check connection
            if not _are_users_connected(current_user.user_id, partner_id):
                return jsonify({'error': 'Users are not connected'}), 403
            
            # Get query parameters
            message_type = request.args.get('type', 'all')  # 'chat', 'remark', or 'all'
            since = request.args.get('since')
            limit = int(request.args.get('limit', 50))
            
            # Build query
            query = Message.query.filter(
                or_(
                    and_(Message.sender_id == str(current_user.user_id), Message.receiver_id == str(partner_id)),
                    and_(Message.sender_id == str(partner_id), Message.receiver_id == str(current_user.user_id))
                )
            )
            
            # Filter by message type
            if message_type in ['chat', 'remark']:
                query = query.filter(Message.message_type == message_type)
            
            # Filter by timestamp if since is provided
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    query = query.filter(Message.timestamp > since_dt)
                except ValueError:
                    return jsonify({'error': 'Invalid since timestamp format'}), 400
            
            # Order and limit
            messages = query.order_by(Message.timestamp.asc()).limit(limit).all()
            
            # Format response
            result = []
            for msg in messages:
                msg_data = {
                    'id': msg.id,
                    'sender_id': msg.sender_id,
                    'receiver_id': msg.receiver_id,
                    'message': msg.message,
                    'timestamp': msg.timestamp.isoformat() + 'Z',
                    'message_type': msg.message_type,
                    'read': msg.read
                }
                
                # Include bill info if it's a remark
                if msg.bill_id and msg.bill:
                    msg_data['bill'] = {
                        'id': msg.bill.bill_id,
                        'bill_number': msg.bill.bill_number,
                        'total_amount': float(msg.bill.total_amount),
                        'bill_date': msg.bill.bill_date.isoformat() if msg.bill.bill_date else None
                    }
                
                result.append(msg_data)
            
            return jsonify(result), 200
            
        except Exception as e:
            current_app.logger.error(f"Error getting conversation: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @bp.route('/messages/clients')
    @login_required
    def get_clients():
        """Get list of connected clients for CA with unread message counts."""
        try:
            current_app.logger.info(f"Getting clients for user {current_user.user_id}, role: {current_user.role}")
            
            if current_user.role != 'CA':
                return jsonify({'error': 'Only CAs can access client list'}), 403
            
            ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
            if not ca:
                current_app.logger.error(f"CA profile not found for user {current_user.user_id}")
                return jsonify({'error': 'CA profile not found'}), 404
            
            current_app.logger.info(f"Found CA profile: {ca.ca_id}")
            
            # Get approved connections
            connections = CAConnection.query.filter_by(
                ca_id=ca.ca_id,
                status='approved'
            ).all()
            
            current_app.logger.info(f"Found {len(connections)} approved connections")
            
            clients = []
            for conn in connections:
                shopkeeper = conn.shopkeeper
                if shopkeeper and shopkeeper.user:
                    # Get unread count
                    unread_count = Message.query.filter(
                        Message.sender_id == str(shopkeeper.user.user_id),
                        Message.receiver_id == str(current_user.user_id),
                        Message.read == False
                    ).count()
                    
                    # Get last message
                    last_message = Message.query.filter(
                        or_(
                            and_(Message.sender_id == str(current_user.user_id), Message.receiver_id == str(shopkeeper.user.user_id)),
                            and_(Message.sender_id == str(shopkeeper.user.user_id), Message.receiver_id == str(current_user.user_id))
                        )
                    ).order_by(desc(Message.timestamp)).first()
                    
                    client_data = {
                        'user_id': shopkeeper.user.user_id,
                        'shopkeeper_id': shopkeeper.shopkeeper_id,
                        'shop_name': shopkeeper.shop_name,
                        'username': shopkeeper.user.username,
                        'unread_count': unread_count,
                        'last_message': {
                            'text': last_message.message[:50] + '...' if last_message and len(last_message.message) > 50 else (last_message.message if last_message else ''),
                            'timestamp': last_message.timestamp.isoformat() + 'Z' if last_message else None,
                            'type': last_message.message_type if last_message else None
                        } if last_message else None
                    }
                    clients.append(client_data)
            
            current_app.logger.info(f"Returning {len(clients)} clients")
            
            # Sort by last message timestamp (newest first)
            clients.sort(key=lambda x: x['last_message']['timestamp'] if x['last_message'] else '', reverse=True)
            
            return jsonify(clients), 200
            
        except Exception as e:
            current_app.logger.error(f"Error getting clients: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @bp.route('/messages/mark_read', methods=['PATCH'])
    @login_required
    def mark_messages_read():
        """Mark messages as read."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            partner_id = data.get('partner_id')
            message_ids = data.get('message_ids', [])
            
            if not partner_id:
                return jsonify({'error': 'partner_id is required'}), 400
            
            # Verify partner exists
            partner = User.query.get(partner_id)
            if not partner:
                return jsonify({'error': 'Partner not found'}), 404
            
            # Check connection
            if not _are_users_connected(current_user.user_id, partner_id):
                return jsonify({'error': 'Users are not connected'}), 403
            
            # Build query - mark messages from partner to current user as read
            query = Message.query.filter(
                Message.sender_id == str(partner_id),
                Message.receiver_id == str(current_user.user_id),
                Message.read == False
            )
            
            # If specific message IDs provided, filter by them
            if message_ids:
                query = query.filter(Message.id.in_(message_ids))
            
            # Update messages
            updated_count = query.update({'read': True})
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'updated_count': updated_count
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"Error marking messages as read: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Internal server error'}), 500
    
    @bp.route('/messages/unread_count/<int:partner_id>')
    @login_required
    def get_unread_count(partner_id):
        """Get unread message count with specific partner."""
        try:
            # Verify partner exists
            partner = User.query.get(partner_id)
            if not partner:
                return jsonify({'error': 'Partner not found'}), 404
            
            # Check connection
            if not _are_users_connected(current_user.user_id, partner_id):
                return jsonify({'error': 'Users are not connected'}), 403
            
            # Count unread messages from partner
            unread_count = Message.query.filter(
                Message.sender_id == str(partner_id),
                Message.receiver_id == str(current_user.user_id),
                Message.read == False
            ).count()
            
            return jsonify({'unread_count': unread_count}), 200
            
        except Exception as e:
            current_app.logger.error(f"Error getting unread count: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

def _are_users_connected(user_id1, user_id2):
    """Check if two users are connected via CA-Shopkeeper relationship."""
    try:
        current_app.logger.info(f"Checking connection between users {user_id1} and {user_id2}")
        
        user1 = User.query.get(user_id1)
        user2 = User.query.get(user_id2)
        
        if not user1 or not user2:
            current_app.logger.error(f"One or both users not found: {user1}, {user2}")
            return False
        
        current_app.logger.info(f"User roles: {user1.role}, {user2.role}")
        
        # One must be CA, other must be shopkeeper
        if user1.role == user2.role:
            current_app.logger.error(f"Both users have same role: {user1.role}")
            return False
        
        ca_user = user1 if user1.role == 'CA' else user2
        shopkeeper_user = user2 if user1.role == 'CA' else user1
        
        # Get CA and Shopkeeper records
        ca = CharteredAccountant.query.filter_by(user_id=ca_user.user_id).first()
        shopkeeper = Shopkeeper.query.filter_by(user_id=shopkeeper_user.user_id).first()
        
        if not ca or not shopkeeper:
            current_app.logger.error(f"CA or Shopkeeper record not found: CA={ca}, Shopkeeper={shopkeeper}")
            return False
        
        current_app.logger.info(f"Found CA: {ca.ca_id}, Shopkeeper: {shopkeeper.shopkeeper_id}")
        
        # Check for approved connection
        connection = CAConnection.query.filter_by(
            ca_id=ca.ca_id,
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='approved'
        ).first()
        
        current_app.logger.info(f"Connection found: {connection is not None}")
        
        return connection is not None
        
    except Exception as e:
        current_app.logger.error(f"Error checking user connection: {str(e)}")
        return False

def _can_access_bill(user_id, bill):
    """Check if user can access a specific bill."""
    try:
        user = User.query.get(user_id)
        if not user:
            return False
        
        if user.role == 'shopkeeper':
            # Shopkeepers can access their own bills
            shopkeeper = Shopkeeper.query.filter_by(user_id=user_id).first()
            return shopkeeper and bill.shopkeeper_id == shopkeeper.shopkeeper_id
        
        elif user.role == 'CA':
            # CAs can access bills of connected shopkeepers
            ca = CharteredAccountant.query.filter_by(user_id=user_id).first()
            if not ca:
                return False
            
            # Check if CA is connected to the bill's shopkeeper
            connection = CAConnection.query.filter_by(
                ca_id=ca.ca_id,
                shopkeeper_id=bill.shopkeeper_id,
                status='approved'
            ).first()
            
            return connection is not None
        
        return False
        
    except Exception as e:
        current_app.logger.error(f"Error checking bill access: {str(e)}")
        return False