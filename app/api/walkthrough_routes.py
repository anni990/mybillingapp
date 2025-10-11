"""
Walkthrough API endpoints.
Handles walkthrough completion tracking and related functionality.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db

# Create blueprint for walkthrough API
walkthrough_bp = Blueprint('walkthrough_api', __name__, url_prefix='/api')

@walkthrough_bp.route('/mark_walkthrough_completed', methods=['POST'])
@login_required
def mark_walkthrough_completed():
    """Mark walkthrough as completed for current user."""
    try:
        current_user.walkthrough_completed = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Walkthrough marked as completed'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@walkthrough_bp.route('/reset_walkthrough', methods=['POST'])
@login_required
def reset_walkthrough():
    """Reset walkthrough status for current user (for testing)."""
    try:
        current_user.walkthrough_completed = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Walkthrough reset successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@walkthrough_bp.route('/walkthrough/complete', methods=['POST'])
@login_required
def complete_walkthrough():
    """Mark walkthrough as completed for current user."""
    try:
        current_user.walkthrough_completed = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Walkthrough completed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@walkthrough_bp.route('/walkthrough_status', methods=['GET'])
@login_required
def walkthrough_status():
    """Get walkthrough status for current user."""
    try:
        # Check if user should see walkthrough
        # For now, use simple logic - show if no bills exist
        from app.models import Bill, Shopkeeper
        
        if current_user.role == 'shopkeeper':
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if shopkeeper:
                bill_count = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).count()
                show_walkthrough = bill_count == 0 and not current_user.walkthrough_completed
            else:
                show_walkthrough = True and not current_user.walkthrough_completed
        else:
            show_walkthrough = False
            
        return jsonify({
            'success': True, 
            'show_walkthrough': show_walkthrough,
            'user_role': current_user.role,
            'walkthrough_completed': current_user.walkthrough_completed
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500