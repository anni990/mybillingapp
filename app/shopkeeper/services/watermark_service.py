"""
Watermark service for managing watermark display logic based on subscription tiers.
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from app.models import Shopkeeper


class WatermarkService:
    """Service class for managing watermark logic based on subscription plans."""
    
    @staticmethod
    def get_watermark_rules(subscription_plan: str) -> Dict[str, Any]:
        """Get watermark rules based on subscription plan.
        
        Args:
            subscription_plan: The subscription plan ('free', 'lite', 'gold')
            
        Returns:
            Dict containing watermark rules for the plan
        """
        rules = {
            'free': {
                'watermark_mandatory': True,
                'can_disable': False,
                'default_enabled': True,
                'available_types': ['diagonal', 'bottom', 'centered'],
                'description': 'Free users must show watermark - cannot be disabled'
            },
            'lite': {
                'watermark_mandatory': False,
                'can_disable': True,
                'default_enabled': False,
                'available_types': ['diagonal', 'bottom', 'centered'],
                'description': 'Lite users can choose to show/hide watermark'
            },
            'gold': {
                'watermark_mandatory': False,
                'can_disable': True,
                'default_enabled': False,
                'available_types': ['diagonal', 'bottom', 'centered'],
                'description': 'Gold users can choose to show/hide watermark'
            }
        }
        
        return rules.get(subscription_plan.lower(), rules['free'])
    
    @staticmethod
    def can_change_watermark_setting(shopkeeper: Shopkeeper) -> bool:
        """Check if shopkeeper can change watermark enabled/disabled setting.
        
        Args:
            shopkeeper: Shopkeeper model instance
            
        Returns:
            Bool indicating if watermark setting can be changed
        """
        rules = WatermarkService.get_watermark_rules(shopkeeper.subscription_plan)
        return rules['can_disable']
    
    @staticmethod
    def get_default_watermark_settings(subscription_plan: str) -> Dict[str, Any]:
        """Get default watermark settings for new shopkeeper based on plan.
        
        Args:
            subscription_plan: The subscription plan
            
        Returns:
            Dict containing default watermark settings
        """
        rules = WatermarkService.get_watermark_rules(subscription_plan)
        
        return {
            'watermark_enabled': rules['default_enabled'],
            'watermark_type': 'diagonal'  # Default to diagonal style
        }
    
    @staticmethod
    def validate_watermark_update(shopkeeper: Shopkeeper, watermark_enabled: bool, watermark_type: str) -> Dict[str, Any]:
        """Validate watermark update request.
        
        Args:
            shopkeeper: Shopkeeper model instance
            watermark_enabled: Requested watermark enabled status
            watermark_type: Requested watermark type
            
        Returns:
            Dict with validation result and message
        """
        rules = WatermarkService.get_watermark_rules(shopkeeper.subscription_plan)
        
        # For free users, watermark must be enabled
        if shopkeeper.subscription_plan == 'free' and not watermark_enabled:
            return {
                'valid': False,
                'message': 'Free users cannot disable watermark. Upgrade to Lite or Gold plan to remove watermarks.'
            }
        
        # Check if watermark type is valid
        if watermark_type not in rules['available_types']:
            return {
                'valid': False,
                'message': f'Invalid watermark type. Available types: {", ".join(rules["available_types"])}'
            }
        
        return {
            'valid': True,
            'message': 'Watermark settings are valid'
        }
    
    @staticmethod
    def get_watermark_display_info(shopkeeper: Shopkeeper) -> Dict[str, Any]:
        """Get complete watermark display information for templates.
        
        Args:
            shopkeeper: Shopkeeper model instance
            
        Returns:
            Dict containing all watermark display information
        """
        rules = WatermarkService.get_watermark_rules(shopkeeper.subscription_plan)
        
        return {
            'show_watermark': shopkeeper.watermark_enabled,
            'watermark_type': shopkeeper.watermark_type,
            'can_change_setting': rules['can_disable'],
            'is_mandatory': rules['watermark_mandatory'],
            'available_types': rules['available_types'],
            'subscription_plan': shopkeeper.subscription_plan,
            'plan_description': rules['description']
        }
    
    @staticmethod
    def initialize_watermark_for_new_shopkeeper(shopkeeper: Shopkeeper) -> None:
        """Initialize watermark settings for newly created shopkeeper.
        
        Args:
            shopkeeper: Shopkeeper model instance (before saving to DB)
        """
        defaults = WatermarkService.get_default_watermark_settings(shopkeeper.subscription_plan)
        
        shopkeeper.watermark_enabled = defaults['watermark_enabled']
        shopkeeper.watermark_type = defaults['watermark_type']
    
    @staticmethod
    def get_watermark_types() -> Dict[str, str]:
        """Get available watermark types with descriptions.
        
        Returns:
            Dict mapping watermark types to their descriptions
        """
        return {
            'diagonal': 'Diagonal Repeated Pattern',
            'bottom': 'Small Logo at Bottom',
            'centered': 'Large Centered Background'
        }