"""
CA Client Service - Manage CA-owned shopkeeper profiles.
Handles client registration with User account creation.
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, Tuple, Optional
import secrets
import string

from app.models import Shopkeeper, CAConnection, CharteredAccountant, User
from app.extensions import db
from werkzeug.security import generate_password_hash


class CAClientService:
    """Service class for CA client management."""
    
    @staticmethod
    def create_client(ca_id: int, client_data: Dict) -> Tuple[Shopkeeper, bool]:
        """Create a new shopkeeper client with User account."""
        try:
            # Generate username if not provided
            username = client_data.get('username')
            if not username:
                # Generate username from shop name
                shop_name = client_data['shop_name'].lower().replace(' ', '_')
                username = f"{shop_name}_{secrets.token_hex(4)}"
            
            # Generate password if not provided
            password = client_data.get('password')
            if not password:
                password = CAClientService._generate_password()
            
            # Create User account first
            user = User(
                username=username,
                email=client_data['email'],
                password_hash=generate_password_hash(password),
                role='shopkeeper',
                plain_password=password  # Store plain password for CA access
            )
            
            db.session.add(user)
            db.session.flush()  # Get user_id
            
            # Create shopkeeper profile
            shopkeeper = Shopkeeper(
                user_id=user.user_id,
                shop_name=client_data['shop_name'],
                owner_name=client_data.get('owner_name'),
                business_type=client_data.get('business_type'),
                business_address=client_data.get('business_address'),
                owner_address=client_data.get('owner_address'),
                established_year=client_data.get('established_year'),
                pan_number=client_data.get('pan_number'),
                gst_number=client_data.get('gst_number'),
                contact_number=client_data.get('contact_number'),
                city=client_data.get('city'),
                state=client_data.get('state'),
                pincode=client_data.get('pincode'),
                domain=client_data.get('domain', 'General'),
                address=client_data.get('business_address')  # Backward compatibility
            )
            
            db.session.add(shopkeeper)
            db.session.flush()  # Get shopkeeper_id
            
            # Create approved CA connection
            connection = CAConnection(
                ca_id=ca_id,
                shopkeeper_id=shopkeeper.shopkeeper_id,
                status='approved',
                created_at=datetime.utcnow()
            )
            
            db.session.add(connection)
            db.session.commit()
            
            return shopkeeper, True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating client: {str(e)}")
            return None, False
    
    @staticmethod
    def _generate_password(length: int = 12) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def validate_client_data(client_data: Dict) -> Tuple[bool, str]:
        """Validate client registration data."""
        required_fields = ['shop_name', 'contact_number', 'email']
        
        for field in required_fields:
            if not client_data.get(field):
                return False, f"{field.replace('_', ' ').title()} is required"
        
        # Validate email format
        email = client_data.get('email', '')
        if '@' not in email or '.' not in email:
            return False, "Please enter a valid email address"
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return False, "Email address already exists in system"
        
        # Check if username already exists (if provided)
        username = client_data.get('username')
        if username:
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                return False, "Username already exists"
        
        # Validate contact number format
        contact = client_data.get('contact_number', '')
        if len(contact) < 10:
            return False, "Contact number must be at least 10 digits"
        
        # Validate GST number if provided
        gst_number = client_data.get('gst_number')
        if gst_number and len(gst_number) != 15:
            return False, "GST number must be 15 characters"
        
        return True, ""
    
    @staticmethod
    def get_ca_clients(ca_id: int) -> list:
        """Get all clients for a specific CA with credentials."""
        connections = CAConnection.query.filter_by(
            ca_id=ca_id, 
            status='approved'
        ).all()
        
        clients = []
        for conn in connections:
            shop = Shopkeeper.query.get(conn.shopkeeper_id)
            if shop:
                user = User.query.get(shop.user_id) if shop.user_id else None
                clients.append({
                    'shopkeeper_id': shop.shopkeeper_id,
                    'shop_name': shop.shop_name,
                    'owner_name': shop.owner_name,
                    'business_type': shop.business_type,
                    'contact_number': shop.contact_number,
                    'gst_number': shop.gst_number,
                    'city': shop.city,
                    'state': shop.state,
                    'created_at': conn.created_at,
                    # Credentials for CA access
                    'username': user.username if user else 'N/A',
                    'email': user.email if user else 'N/A',
                    'password': user.plain_password if user else 'N/A'
                })
        
        return clients
