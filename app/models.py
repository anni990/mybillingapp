from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

from app.extensions import db
# ... define models using this db

class User(db.Model, UserMixin):
    """User account: shopkeeper, CA, or employee."""
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('shopkeeper', 'CA', 'employee'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    plain_password = db.Column(db.String(255), nullable=True)  # Only for employees
    # Relationships
    shopkeeper = db.relationship('Shopkeeper', backref='user', uselist=False)
    ca = db.relationship('CharteredAccountant', backref='user', uselist=False)
    ca_employee = db.relationship('CAEmployee', backref='user', uselist=False)

    def get_id(self):
        return str(self.user_id)

class Shopkeeper(db.Model):
    """Shopkeeper profile."""
    __tablename__ = 'shopkeepers'
    shopkeeper_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    shop_name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(50))
    address = db.Column(db.String(255))
    gst_number = db.Column(db.String(20))
    contact_number = db.Column(db.String(20))
    gst_doc_path = db.Column(db.String(255))
    pan_doc_path = db.Column(db.String(255))
    address_proof_path = db.Column(db.String(255))
    logo_path = db.Column(db.String(255))
    aadhaar_dl_path = db.Column(db.String(255))
    selfie_path = db.Column(db.String(255))
    gumasta_path = db.Column(db.String(255))
    udyam_path = db.Column(db.String(255))
    bank_statement_path = db.Column(db.String(255))
    is_verified = db.Column(db.Boolean, default=False)
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    ifsc_code = db.Column(db.String(20))
    template_choice = db.Column(db.String(20), default='template2')
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    # Relationships
    products = db.relationship('Product', backref='shopkeeper', cascade='all, delete-orphan')
    bills = db.relationship('Bill', backref='shopkeeper', cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='shopkeeper', cascade='all, delete-orphan')
    ca_connections = db.relationship('CAConnection', backref='shopkeeper', cascade='all, delete-orphan')
    employee_clients = db.relationship('EmployeeClient', backref='shopkeeper', cascade='all, delete-orphan')

class CharteredAccountant(db.Model):
    """Chartered Accountant profile."""
    __tablename__ = 'chartered_accountants'
    ca_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    firm_name = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    gst_number = db.Column(db.String(20))
    pan_number = db.Column(db.String(20))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    # New fields for document uploads and GSTIN
    aadhaar_file = db.Column(db.String(255))
    pan_file = db.Column(db.String(255))
    icai_certificate_file = db.Column(db.String(255))
    cop_certificate_file = db.Column(db.String(255))
    gstin = db.Column(db.String(30))
    business_reg_file = db.Column(db.String(255))
    bank_details_file = db.Column(db.String(255))
    photo_file = db.Column(db.String(255))
    signature_file = db.Column(db.String(255))
    office_address_proof_file = db.Column(db.String(255))
    self_declaration_file = db.Column(db.String(255))
    # Relationships
    employees = db.relationship('CAEmployee', backref='ca', cascade='all, delete-orphan')
    ca_connections = db.relationship('CAConnection', backref='ca', cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='ca', cascade='all, delete-orphan')

class CAEmployee(db.Model):
    """CA Employee profile."""
    __tablename__ = 'ca_employees'
    employee_id = db.Column(db.Integer, primary_key=True)
    ca_id = db.Column(db.Integer, db.ForeignKey('chartered_accountants.ca_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    # Relationships
    employee_clients = db.relationship('EmployeeClient', backref='employee', cascade='all, delete-orphan')

class EmployeeClient(db.Model):
    """Mapping between CA employees and shopkeepers."""
    __tablename__ = 'employee_clients'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('ca_employees.employee_id', ondelete='CASCADE'), nullable=False)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'), nullable=False)

class Product(db.Model):
    """Product and stock for shopkeepers."""
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(50))
    price = db.Column(db.Numeric(10,2), nullable=False)
    stock_qty = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=0)
    gst_rate = db.Column(db.Numeric(5,2), default=0)  # New field for GST rate
    hsn_code = db.Column(db.String(20))  # HSN code for GST
    # Relationships
    bill_items = db.relationship('BillItem', backref='product', cascade='all, delete-orphan')

class Bill(db.Model):
    """Bill created by shopkeepers."""
    __tablename__ = 'bills'
    bill_id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=True)  # New field for registered customers
    bill_number = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(100))
    customer_address=db.Column(db.String(100), nullable=True)
    customer_gstin=db.Column(db.String(50), nullable=True)
    customer_contact = db.Column(db.String(20))
    bill_date = db.Column(db.Date, nullable=False)
    gst_type = db.Column(db.Enum('GST', 'Non-GST'), nullable=False)
    total_amount = db.Column(db.Numeric(12,2), nullable=False)
    payment_status = db.Column(db.String(20), default='PAID')  # 'PAID', 'PARTIAL', 'UNPAID'
    paid_amount = db.Column(db.Numeric(10,2), default=0.00)  # Tracking payments
    due_amount = db.Column(db.Numeric(10,2), default=0.00)   # Tracking dues
    # Relationships
    bill_items = db.relationship('BillItem', backref='bill', cascade='all, delete-orphan')

class BillItem(db.Model):
    """Items in a bill."""
    __tablename__ = 'bill_items'
    bill_item_id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.bill_id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=True)  # Made nullable for custom products
    custom_product_name = db.Column(db.String(100), nullable=True)  # For custom products not in products table
    custom_gst_rate = db.Column(db.Numeric(5,2), nullable=True)  # GST rate for custom products
    custom_hsn_code = db.Column(db.String(20), nullable=True)  # HSN code for custom products
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(12,2), nullable=False)

class CAConnection(db.Model):
    """Connection between shopkeepers and CAs."""
    __tablename__ = 'ca_connections'
    id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'), nullable=False)
    ca_id = db.Column(db.Integer, db.ForeignKey('chartered_accountants.ca_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Document(db.Model):
    """Documents shared between shopkeepers and CAs."""
    __tablename__ = 'documents'
    document_id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'))
    ca_id = db.Column(db.Integer, db.ForeignKey('chartered_accountants.ca_id', ondelete='CASCADE'))
    document_name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

class ShopConnection(db.Model):
    """Connection requests from shopkeepers to CAs."""
    __tablename__ = 'shop_connections'
    id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'), nullable=False)
    ca_id = db.Column(db.Integer, db.ForeignKey('chartered_accountants.ca_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class GSTFilingStatus(db.Model):
    __tablename__ = 'gst_filing_status'
    id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('ca_employees.employee_id', ondelete='SET NULL'))
    month = db.Column(db.String(7), nullable=False)  # Format: YYYY-MM
    status = db.Column(db.Enum('Filed', 'Not Filed'), default='Not Filed', nullable=False)
    filed_at = db.Column(db.DateTime)
    shopkeeper = db.relationship('Shopkeeper', backref='gst_filing_statuses')
    employee = db.relationship('CAEmployee', backref='gst_filing_statuses')

class Customer(db.Model):
    """Customer model for shopkeeper's customer management."""
    __tablename__ = 'customers'
    
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    total_balance = db.Column(db.Numeric(10, 2), default=0.00)
    
    # Relationships
    shopkeeper = db.relationship('User', backref='customers')
    ledger_entries = db.relationship('CustomerLedger', backref='customer', lazy='dynamic')
    bills = db.relationship('Bill', backref='customer')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('shopkeeper_id', 'phone', name='unique_shopkeeper_phone'),
    )

class CustomerLedger(db.Model):
    __tablename__ = 'customer_ledger'
    
    ledger_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_no = db.Column(db.String(50), nullable=True)
    particulars = db.Column(db.String(255), nullable=False)
    debit_amount = db.Column(db.Numeric(10, 2), default=0.00)
    credit_amount = db.Column(db.Numeric(10, 2), default=0.00)
    balance_amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'PURCHASE', 'PAYMENT', 'ADJUSTMENT'
    reference_bill_id = db.Column(db.Integer, db.ForeignKey('bills.bill_id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    shopkeeper = db.relationship('User')
    reference_bill = db.relationship('Bill')
