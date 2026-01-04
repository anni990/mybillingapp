"""
Payment service for handling Razorpay payment operations.
This service handles order creation, payment verification, and subscription upgrades.
"""

import razorpay
import hmac
import hashlib
import logging
import pytz
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple, Any
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import SubscriptionPayment, PaymentAuditLog, Shopkeeper
from app.shopkeeper.services.subscription_service import SubscriptionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentService:
    """Service class for handling Razorpay payment operations."""
    
    @staticmethod
    def _get_ist_now():
        """Get current datetime in IST timezone."""
        ist = pytz.timezone('Asia/Kolkata')
        return datetime.now(ist)
    
    @staticmethod
    def _get_ist_naive_now():
        """Get current datetime in IST as naive datetime for database storage."""
        ist = pytz.timezone('Asia/Kolkata')
        return datetime.now(ist).replace(tzinfo=None)
    
    @staticmethod
    def _convert_to_ist(dt):
        """Convert datetime to IST timezone."""
        if dt is None:
            return None
        ist = pytz.timezone('Asia/Kolkata')
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            utc_dt = pytz.utc.localize(dt)
            return utc_dt.astimezone(ist)
        return dt.astimezone(ist)
    
    @staticmethod
    def _get_razorpay_client():
        """Get configured Razorpay client instance."""
        try:
            client = razorpay.Client(
                auth=(
                    current_app.config['RAZORPAY_KEY_ID'],
                    current_app.config['RAZORPAY_SECRET_KEY']
                )
            )
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Razorpay client: {str(e)}")
            raise Exception("Payment gateway initialization failed")
    
    @staticmethod
    def create_razorpay_order(shopkeeper: Shopkeeper, plan_type: str) -> Dict[str, Any]:
        """
        Create a Razorpay order for subscription payment.
        
        Args:
            shopkeeper: Shopkeeper instance
            plan_type: Plan type ('lite' or 'gold')
            
        Returns:
            Dict containing order details and payment record
        """
        try:
            # Validate plan type
            if plan_type not in ['lite', 'gold']:
                raise ValueError("Invalid plan type. Must be 'lite' or 'gold'")
            
            # Get plan pricing from config
            plan_config = current_app.config['SUBSCRIPTION_PLANS'].get(plan_type)
            if not plan_config:
                raise ValueError(f"Plan configuration not found for {plan_type}")
            
            amount_inr = plan_config['price']
            amount_paise = int(amount_inr * 100)  # Convert to paise (Razorpay requirement)
            
            # Create Razorpay order
            client = PaymentService._get_razorpay_client()
            
            order_data = {
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': f"sub_{shopkeeper.shopkeeper_id}_{int(PaymentService._get_ist_now().timestamp())}",
                'notes': {
                    'shopkeeper_id': shopkeeper.shopkeeper_id,
                    'plan_type': plan_type,
                    'current_plan': shopkeeper.subscription_plan
                }
            }
            
            razorpay_order = client.order.create(data=order_data)
            
            # Create payment record in database
            payment_record = SubscriptionPayment(
                shopkeeper_id=shopkeeper.shopkeeper_id,
                razorpay_order_id=razorpay_order['id'],
                plan_type=plan_type,
                amount=Decimal(str(amount_inr)),
                currency='INR',
                status='created',
                payment_metadata={
                    'receipt': order_data['receipt'],
                    'created_via': 'web_interface'
                },
                created_at=PaymentService._get_ist_naive_now()
            )
            
            db.session.add(payment_record)
            db.session.commit()
            
            # Create audit log
            PaymentService._create_audit_log(
                payment_record.payment_id,
                old_status=None,
                new_status='created',
                change_reason='Order created via Razorpay'
            )
            
            logger.info(f"Created Razorpay order {razorpay_order['id']} for shopkeeper {shopkeeper.shopkeeper_id}")
            
            return {
                'success': True,
                'order_id': razorpay_order['id'],
                'amount': amount_paise,
                'currency': 'INR',
                'key_id': current_app.config['RAZORPAY_KEY_ID'],
                'payment_record_id': payment_record.payment_id,
                'plan_name': plan_config['name'],
                'plan_price': amount_inr
            }
            
        except ValueError as e:
            logger.error(f"Validation error in create_razorpay_order: {str(e)}")
            return {'success': False, 'error': str(e)}
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay BadRequest error: {str(e)}")
            return {'success': False, 'error': 'Invalid payment request'}
        except Exception as e:
            logger.error(f"Unexpected error in create_razorpay_order: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': 'Payment order creation failed'}
    
    @staticmethod
    def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, 
                                razorpay_signature: str) -> bool:
        """
        Verify Razorpay payment signature for security.
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from Razorpay
            
        Returns:
            bool: True if signature is valid
        """
        try:
            # Create signature verification string
            message = f"{razorpay_order_id}|{razorpay_payment_id}"
            
            # Generate expected signature using webhook secret
            secret = current_app.config['RAZORPAY_SECRET_KEY']
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            is_valid = hmac.compare_digest(expected_signature, razorpay_signature)
            
            if not is_valid:
                logger.warning(f"Invalid payment signature for order {razorpay_order_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying payment signature: {str(e)}")
            return False
    
    @staticmethod
    def process_successful_payment(razorpay_order_id: str, razorpay_payment_id: str, 
                                 razorpay_signature: str, payment_method: str = None) -> Dict[str, Any]:
        """
        Process successful payment and upgrade subscription.
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from Razorpay
            payment_method: Payment method used
            
        Returns:
            Dict containing success status and details
        """
        try:
            # Find payment record
            payment_record = SubscriptionPayment.query.filter_by(
                razorpay_order_id=razorpay_order_id
            ).first()
            
            if not payment_record:
                return {'success': False, 'error': 'Payment record not found'}
            
            # Verify signature
            if not PaymentService.verify_payment_signature(
                razorpay_order_id, razorpay_payment_id, razorpay_signature
            ):
                return {'success': False, 'error': 'Payment signature verification failed'}
            
            # Update payment record
            old_status = payment_record.status
            payment_record.razorpay_payment_id = razorpay_payment_id
            payment_record.razorpay_signature = razorpay_signature
            payment_record.status = 'captured'
            payment_record.payment_method = payment_method
            payment_record.updated_at = PaymentService._get_ist_naive_now()
            
            # Get shopkeeper
            shopkeeper = payment_record.shopkeeper
            if not shopkeeper:
                return {'success': False, 'error': 'Shopkeeper not found'}
            
            # Update subscription plan
            upgrade_result = SubscriptionService.update_plan_with_payment_validation(shopkeeper, payment_record.plan_type)
            if not upgrade_result:
                return {'success': False, 'error': 'Subscription upgrade failed'}
            
            # Set subscription expiry (30 days from now in IST)
            shopkeeper.subscription_expires_at = PaymentService._get_ist_naive_now() + timedelta(days=30)
            shopkeeper.last_payment_id = payment_record.payment_id
            
            db.session.commit()
            
            # Create audit log
            PaymentService._create_audit_log(
                payment_record.payment_id,
                old_status=old_status,
                new_status='captured',
                change_reason='Payment captured successfully'
            )
            
            logger.info(f"Successfully processed payment {razorpay_payment_id} for shopkeeper {shopkeeper.shopkeeper_id}")
            
            return {
                'success': True,
                'plan_upgraded': payment_record.plan_type,
                'payment_id': payment_record.payment_id,
                'expires_at': shopkeeper.subscription_expires_at.isoformat() if shopkeeper.subscription_expires_at else None
            }
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in process_successful_payment: {str(e)}")
            return {'success': False, 'error': 'Database operation failed'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in process_successful_payment: {str(e)}")
            return {'success': False, 'error': 'Payment processing failed'}
    
    @staticmethod
    def handle_payment_failure(razorpay_order_id: str, failure_reason: str = None) -> Dict[str, Any]:
        """
        Handle failed payment by updating status.
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            failure_reason: Reason for payment failure
            
        Returns:
            Dict containing success status
        """
        try:
            payment_record = SubscriptionPayment.query.filter_by(
                razorpay_order_id=razorpay_order_id
            ).first()
            
            if not payment_record:
                return {'success': False, 'error': 'Payment record not found'}
            
            old_status = payment_record.status
            payment_record.status = 'failed'
            payment_record.failure_reason = failure_reason
            payment_record.updated_at = PaymentService._get_ist_naive_now()
            
            db.session.commit()
            
            # Create audit log
            PaymentService._create_audit_log(
                payment_record.payment_id,
                old_status=old_status,
                new_status='failed',
                change_reason=failure_reason or 'Payment failed'
            )
            
            logger.info(f"Marked payment {razorpay_order_id} as failed")
            
            return {'success': True}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error handling payment failure: {str(e)}")
            return {'success': False, 'error': 'Failed to update payment status'}
    
    @staticmethod
    def get_payment_status(razorpay_order_id: str) -> Optional[SubscriptionPayment]:
        """
        Get payment record by order ID.
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            
        Returns:
            SubscriptionPayment record or None
        """
        return SubscriptionPayment.query.filter_by(
            razorpay_order_id=razorpay_order_id
        ).first()
    
    @staticmethod
    def get_shopkeeper_payment_history(shopkeeper: Shopkeeper, limit: int = 10) -> list:
        """
        Get payment history for a shopkeeper.
        
        Args:
            shopkeeper: Shopkeeper instance
            limit: Maximum number of records to return
            
        Returns:
            List of payment records
        """
        return SubscriptionPayment.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).order_by(SubscriptionPayment.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def _create_audit_log(payment_id: int, old_status: str, new_status: str, 
                         change_reason: str, webhook_event_id: str = None) -> None:
        """
        Create audit log entry for payment status change.
        
        Args:
            payment_id: Payment record ID
            old_status: Previous status
            new_status: New status  
            change_reason: Reason for change
            webhook_event_id: Webhook event ID if applicable
        """
        try:
            audit_log = PaymentAuditLog(
                payment_id=payment_id,
                old_status=old_status,
                new_status=new_status,
                change_reason=change_reason,
                webhook_event_id=webhook_event_id,
                created_at=PaymentService._get_ist_naive_now()
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def validate_webhook_signature(payload: str, signature: str) -> bool:
        """
        Validate webhook signature from Razorpay.
        
        Args:
            payload: Webhook payload
            signature: X-Razorpay-Signature header value
            
        Returns:
            bool: True if signature is valid
        """
        try:
            webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET')
            if not webhook_secret:
                logger.error("Webhook secret not configured")
                return False
            
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Error validating webhook signature: {str(e)}")
            return False