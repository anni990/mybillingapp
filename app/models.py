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
    pdf_file_path = db.Column(db.String(255))
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
    status = db.Column(db.Enum('pending', 'approved'), nullable=False, default='pending')

class Document(db.Model):
    """Documents shared between shopkeepers and CAs."""
    __tablename__ = 'documents'
    document_id = db.Column(db.Integer, primary_key=True)
    shopkeeper_id = db.Column(db.Integer, db.ForeignKey('shopkeepers.shopkeeper_id', ondelete='CASCADE'))
    ca_id = db.Column(db.Integer, db.ForeignKey('chartered_accountants.ca_id', ondelete='CASCADE'))
    document_name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
