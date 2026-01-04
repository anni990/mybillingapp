"""
Subscription Service
Centralized service for managing shopkeeper subscription plans, limits, and validations.
"""
from datetime import date, datetime
from typing import Dict, Optional, Tuple
from flask import flash
from app.models import Shopkeeper
from app.extensions import db


class SubscriptionService:
    """Service class for subscription plan management and validation."""
    
    # Plan definitions with features and limits
    PLAN_FEATURES = {
        'free': {
            'name': 'Free MBA',
            'daily_gst_limit': 5,
            'non_gst_limit': None,  # Unlimited
            'watermark': True,
            'features': {
                'gst_billing': True,
                'non_gst_billing': True,
                'inventory_management': False,
                'customer_ledger': False,
                'ca_connectivity': False,
                'custom_templates': False,
                'reports': False
            }
        },
        'lite': {
            'name': 'MBA Lite',
            'daily_gst_limit': None,  # Unlimited
            'non_gst_limit': None,  # Unlimited
            'watermark': False,
            'features': {
                'gst_billing': True,
                'non_gst_billing': True,
                'inventory_management': True,
                'customer_ledger': True,
                'ca_connectivity': True,
                'custom_templates': True,
                'reports': True
            }
        },
        'gold': {
            'name': 'MBA Gold',
            'daily_gst_limit': None,  # Unlimited
            'non_gst_limit': None,  # Unlimited
            'watermark': False,
            'features': {
                'gst_billing': True,
                'non_gst_billing': True,
                'inventory_management': True,
                'customer_ledger': True,
                'ca_connectivity': True,
                'custom_templates': True,
                'reports': True,
                'ai_scan_bills': True,
                'advanced_analytics': True
            }
        }
    }
    
    @staticmethod
    def get_plan_info(plan: str) -> Dict:
        """Get plan information and features."""
        return SubscriptionService.PLAN_FEATURES.get(plan, SubscriptionService.PLAN_FEATURES['free'])
    
    @staticmethod
    def reset_daily_counter_if_needed(shopkeeper: Shopkeeper) -> None:
        """Reset daily bill counter if date has changed."""
        today = date.today()
        
        if shopkeeper.last_bill_date != today:
            shopkeeper.daily_gst_bill_count = 0
            shopkeeper.last_bill_date = today
            db.session.commit()
    
    @staticmethod
    def can_create_gst_bill(shopkeeper: Shopkeeper) -> Tuple[bool, Optional[str]]:
        """
        Check if shopkeeper can create a GST bill based on their plan.
        Returns (can_create, error_message)
        """
        # Reset counter if needed
        SubscriptionService.reset_daily_counter_if_needed(shopkeeper)
        
        plan_info = SubscriptionService.get_plan_info(shopkeeper.subscription_plan)
        daily_limit = plan_info['daily_gst_limit']
        
        # Unlimited plans
        if daily_limit is None:
            return True, None
            
        # Check daily limit for free plan
        if shopkeeper.daily_gst_bill_count >= daily_limit:
            return False, f"Daily GST bill limit reached ({daily_limit} bills). Upgrade to MBA Lite for unlimited billing."
            
        return True, None
    
    @staticmethod
    def increment_gst_bill_counter(shopkeeper: Shopkeeper) -> None:
        """Increment the daily GST bill counter."""
        SubscriptionService.reset_daily_counter_if_needed(shopkeeper)
        shopkeeper.daily_gst_bill_count += 1
        shopkeeper.last_bill_date = date.today()
        db.session.commit()
    
    @staticmethod
    def has_feature_access(shopkeeper: Shopkeeper, feature: str) -> bool:
        """Check if shopkeeper has access to a specific feature."""
        plan_info = SubscriptionService.get_plan_info(shopkeeper.subscription_plan)
        return plan_info['features'].get(feature, False)
    
    @staticmethod
    def requires_watermark(shopkeeper: Shopkeeper) -> bool:
        """Check if bills should have watermark."""
        plan_info = SubscriptionService.get_plan_info(shopkeeper.subscription_plan)
        return plan_info['watermark']
    
    @staticmethod
    def get_upgrade_message(required_plan: str) -> str:
        """Get appropriate upgrade message for required plan."""
        messages = {
            'lite': "This feature requires MBA Lite or Gold plan. Upgrade to access inventory management, customer ledger, and CA connectivity.",
            'gold': "This feature requires MBA Gold plan. Upgrade to access AI-powered bill scanning and advanced analytics."
        }
        return messages.get(required_plan, "Please upgrade your plan to access this feature.")
    
    @staticmethod
    def update_plan(shopkeeper: Shopkeeper, new_plan: str, payment_validated: bool = False) -> bool:
        """
        Update shopkeeper's subscription plan with payment validation.
        
        Args:
            shopkeeper: Shopkeeper instance
            new_plan: Target subscription plan
            payment_validated: Whether payment has been validated for paid plans
        """
        if new_plan not in SubscriptionService.PLAN_FEATURES:
            return False
        
        # Payment validation for paid plans
        if new_plan in ['lite', 'gold'] and not payment_validated:
            # For paid plans, require payment validation
            # This prevents direct plan upgrades without payment
            return False
            
        old_plan = shopkeeper.subscription_plan
        shopkeeper.subscription_plan = new_plan
        
        # Reset counters when upgrading
        shopkeeper.daily_gst_bill_count = 0
        shopkeeper.last_bill_date = date.today()
        
        # Handle watermark settings based on plan change
        from .watermark_service import WatermarkService
        
        # If upgrading from free to paid plan, disable watermark by default
        if old_plan == 'free' and new_plan in ['lite', 'gold']:
            shopkeeper.watermark_enabled = False  # Allow paid users to remove watermark
        
        # If downgrading to free plan, force watermark to be enabled
        elif new_plan == 'free':
            shopkeeper.watermark_enabled = True  # Free users must show watermark
        
        try:
            db.session.commit()
            
            # Log subscription change for audit trail
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Subscription updated for shopkeeper {shopkeeper.shopkeeper_id}: {old_plan} -> {new_plan}, payment_validated: {payment_validated}")
            
            return True
        except Exception as e:
            db.session.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update subscription for shopkeeper {shopkeeper.shopkeeper_id}: {str(e)}")
            return False
    
    @staticmethod
    def update_plan_with_payment_validation(shopkeeper: Shopkeeper, new_plan: str) -> bool:
        """
        Update plan with payment validation - used by PaymentService.
        This method bypasses the payment check since it's called after successful payment.
        """
        return SubscriptionService.update_plan(shopkeeper, new_plan, payment_validated=True)
    
    @staticmethod
    def get_usage_stats(shopkeeper: Shopkeeper) -> Dict:
        """Get usage statistics for the shopkeeper."""
        SubscriptionService.reset_daily_counter_if_needed(shopkeeper)
        
        plan_info = SubscriptionService.get_plan_info(shopkeeper.subscription_plan)
        daily_limit = plan_info['daily_gst_limit']
        
        return {
            'plan': shopkeeper.subscription_plan,
            'plan_name': plan_info['name'],
            'daily_gst_used': shopkeeper.daily_gst_bill_count,
            'daily_gst_limit': daily_limit,
            'daily_gst_remaining': None if daily_limit is None else max(0, daily_limit - shopkeeper.daily_gst_bill_count),
            'is_unlimited': daily_limit is None,
            'requires_watermark': plan_info['watermark']
        }