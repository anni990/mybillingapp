from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

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
    bill_number = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(100))
    customer_contact = db.Column(db.String(20))
    bill_date = db.Column(db.Date, nullable=False)
    gst_type = db.Column(db.Enum('GST', 'Non-GST'), nullable=False)
    total_amount = db.Column(db.Numeric(12,2), nullable=False)
    payment_status = db.Column(db.Enum('Paid', 'Unpaid', 'Partial'), nullable=False)
    amount_paid = db.Column(db.Numeric(12,2), nullable=True, default=0)
    amount_unpaid = db.Column(db.Numeric(12,2), nullable=True, default=0)
    # Relationships
    bill_items = db.relationship('BillItem', backref='bill', cascade='all, delete-orphan')

class BillItem(db.Model):
    """Items in a bill."""
    __tablename__ = 'bill_items'
    bill_item_id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.bill_id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
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
