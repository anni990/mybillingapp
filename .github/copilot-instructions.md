# MyBillingApp - AI Developer Guide

## 🏗️ Architecture Overview

MyBillingApp is a multi-tenant Flask ERP system connecting **Shopkeepers**, **Chartered Accountants (CAs)**, and **CA Employees** in a billing and GST management ecosystem. The application follows Flask blueprint architecture with role-based access control.

### Core Business Logic
- **Shopkeepers**: Create bills, manage products/inventory, customer ledgers (khata system), connect with CAs
- **CAs**: Manage multiple shopkeeper clients, employee delegation, GST filing status tracking
- **CA Employees**: Handle assigned shopkeeper accounts, client-specific dashboards
- **Connection System**: Approval-based relationships between shopkeepers and CAs

### Key Architecture Decisions
- **Multi-database support**: Originally SQL Server (commented), now MySQL with potential reversion
- **Document Management**: File uploads to `app/static/uploads/` and `app/static/ca_upload/`
- **Session Management**: Filesystem-based sessions (`flask_session/` directory)
- **Template Organization**: Role-specific template directories (`auth/`, `ca/`, `shopkeeper/`, `home/`)

## 🤖 AI Development Patterns

### Essential Productivity Rules
- **Foreign Key Priority**: Always use `shopkeeper.shopkeeper_id` for bills/products, `shopkeeper.user_id` for customers/ledger
- **Payment Fields**: Use `paid_amount`/`due_amount` consistently (legacy `amount_paid`/`amount_unpaid` removed)
- **Blueprint Routes**: Add to appropriate blueprint (`shopkeeper_bp`, `ca_bp`, `auth_bp`, `api_bp`)
- **Role Decorators**: Apply `@login_required` + `@shopkeeper_required`/`@ca_required` for protected routes
- **Template Naming**: `{blueprint}/{action}.html` (e.g., `shopkeeper/dashboard.html`)
- **Database Transactions**: Use `db.session.commit()` after modifications, handle rollbacks on errors

### Critical File Patterns
```python
# Route structure (app/shopkeeper/routes.py)
@shopkeeper_bp.route('/dashboard')
@login_required
@shopkeeper_required
def dashboard():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    # Always check if shopkeeper exists
    if not shopkeeper:
        return redirect(url_for('auth.login'))
    
    # Use shopkeeper.shopkeeper_id for queries
    bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
    return render_template('shopkeeper/dashboard.html', bills=bills)

# Model relationships (app/models.py)
class Bill(db.Model):
    paid_amount = db.Column(db.Numeric(10,2), default=0.00)  # ✅ Current standard
    due_amount = db.Column(db.Numeric(10,2), default=0.00)   # ✅ Current standard
    # Relationships with cascade deletes
    bill_items = db.relationship('BillItem', backref='bill', cascade='all, delete-orphan')
```

### Development Workflow Commands
```bash
# Start development server (creates tables automatically)
python run.py

# Test database operations
python -c "from app import create_app; app = create_app(); print('App initialized')"

# Check bill payment data
python -c "
from app import create_app, db
from app.models import Bill
app = create_app()
with app.app_context():
    bills = Bill.query.limit(5).all()
    for bill in bills:
        print(f'Bill {bill.bill_id}: paid={bill.paid_amount}, due={bill.due_amount}')
"
```

### JavaScript Integration Patterns
```javascript
// Product search with debouncing (app/static/js/create_bill.js)
let searchTimeout;
productSearch.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.toLowerCase().trim();
    
    if (query.length < 1) {
        productSuggestions.classList.add('hidden');
        return;
    }

    searchTimeout = setTimeout(() => {
        showProductSuggestions(query);
    }, 300);  // 300ms debounce
});
```

### Template Conventions
```django
{# Role-specific base templates #}
{% extends 'shopkeeper/s_base.html' %}

{# Form handling with CSRF #}
<form method="POST">
    {{ form.hidden_tag() }}
    {{ form.product_name.label }}: {{ form.product_name }}
    <button type="submit">Add Product</button>
</form>

{# Responsive design with Tailwind #}
<div class="flex flex-col md:flex-row md:justify-between md:items-center">
    <h1 class="text-2xl md:text-3xl font-bold">Dashboard</h1>
</div>
```

### Business Logic Patterns
```python
# GST calculation with HSN codes
def calculate_gst_amount(price, gst_rate):
    return Decimal(str(price)) * Decimal(str(gst_rate)) / Decimal('100')

# Customer ledger transactions
def create_ledger_entry(customer_id, transaction_type, debit_amount, credit_amount):
    # Calculate running balance
    current_balance = customer.total_balance or Decimal('0')
    new_balance = current_balance + debit_amount - credit_amount
    
    CustomerLedger.create(
        customer_id=customer_id,
        debit_amount=debit_amount,
        credit_amount=credit_amount,
        balance_amount=new_balance,
        transaction_type=transaction_type
    )
```

## 🗄️ Database Architecture

### Critical Relationships
```python
# Primary user hierarchy
User (base) -> Shopkeeper/CharteredAccountant/CAEmployee (profiles)

# Connection patterns
CAConnection: Shopkeeper <-> CA (approval workflow)
EmployeeClient: CAEmployee <-> Shopkeeper (delegation)

# Business transactions
Bill -> BillItem -> Product (inventory tracking)
Customer -> CustomerLedger (credit/debit tracking)
```

### Database Patterns
- **Foreign Key Distinctions**: `customers.shopkeeper_id` → `users.user_id`, `bills.shopkeeper_id` → `shopkeepers.shopkeeper_id`
- **Payment Field Standardization**: Bills use single consistent field set (`paid_amount`/`due_amount`)
- **Soft cascade deletes**: Use `ondelete='CASCADE'` on foreign keys
- **Enum fields**: `role`, `gst_type`, `payment_status`, `transaction_type`
- **Decimal precision**: `db.Numeric(10,2)` for money fields, `db.Numeric(12,2)` for totals
- **MySQL migration**: Connection string uses `pymysql` driver, but ODBC dependencies remain in Dockerfile

### Schema Evolution
- Multiple schema files exist: `schema.sql` (MySQL), `*_schema_sqlserver.sql` (SQL Server variants)
- Customer ledger system added via `CUSTOMER_LEDGER_IMPLEMENTATION.md`
- GST filing status tracking for compliance management

### Current Status (Updated 2025-09-29)
- **✅ Foreign Key Issues Resolved**: All database queries now use correct foreign key references
- **✅ Payment Fields Migration Complete**: Bills table now uses single consistent field set (`paid_amount`/`due_amount`)
- **✅ Schema Compliance**: Database schema matches production schema with all required columns and constraints
- **✅ Migration Applied**: `drop_legacy_payment_fields.sql` created for removing legacy payment fields from existing databases

## � Critical Fixes Applied

### Foreign Key Corrections (2025-09-29)
**Problem**: Code was using incorrect foreign key references causing constraint violations.

**Fixed Queries**:
```python
# ❌ WRONG - was causing foreign key errors
ca_conn = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.user_id)

# ✅ CORRECT - matches production schema
ca_conn = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)

# ❌ WRONG
products = Product.query.filter_by(shopkeeper_id=shopkeeper.user_id)

# ✅ CORRECT  
products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)

# ❌ WRONG
query = Bill.query.filter_by(shopkeeper_id=shopkeeper.user_id)

# ✅ CORRECT
query = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
```

**Key Pattern**: 
- **CA/Shop Connections**: Use `shopkeeper.shopkeeper_id`
- **Bills/Products**: Use `shopkeeper.shopkeeper_id` 
- **Customers/Ledger**: Use `shopkeeper.user_id`

### Payment Field Migration
**Problem**: Database missing legacy payment fields expected by SQLAlchemy models.

**Migration Applied**:
```sql
ALTER TABLE bills 
ADD COLUMN amount_paid DECIMAL(12,2) DEFAULT 0.00 AFTER payment_status,
ADD COLUMN amount_unpaid DECIMAL(12,2) DEFAULT 0.00 AFTER amount_paid;

UPDATE bills SET 
    amount_paid = paid_amount,
    amount_unpaid = due_amount;
```

**Result**: Bills now have both field sets for backward compatibility.

## �📁 File Organization

### Blueprint Structure
```
app/
├── __init__.py              # Flask app factory, blueprint registration
├── config.py               # Environment-based configuration
├── extensions.py           # Shared Flask extensions (db, login_manager, etc.)
├── models.py              # All SQLAlchemy models (245 lines)
├── forms.py               # WTForms for CA functionality
├── utils.py               # Shared utilities
├── auth/routes.py         # Authentication (registration/login)
├── shopkeeper/routes.py   # Shopkeeper functionality (1677 lines)
├── ca/routes.py          # CA functionality (1059 lines)
└── api/routes.py         # API endpoints
```

### Static Assets
- **CSS**: `app/static/css/tailwind.css` (Tailwind CSS framework)
- **JavaScript**: `app/static/js/` (dashboard.js, create_bill.js, sales_reports.js)
- **File Uploads**: `app/static/uploads/` (shopkeeper docs), `app/static/ca_upload/` (CA docs)
- **Images**: `app/static/images/` (login, dashboard, CA assets)

### Template Patterns
- **Base templates**: `*_base.html` files in each role directory
- **Form templates**: Consistent form structure across roles
- **Dashboard templates**: Role-specific dashboards with similar layouts

## 🔧 Development Workflow

### Running the Application
```bash
# Development
python run.py  # Creates tables via db.create_all(), runs on debug mode

# Production
gunicorn run:app  # Gunicorn WSGI server
```

### Database Initialization
```python
# Automatic table creation in run.py
with app.app_context():
    db.create_all()
```

### Environment Configuration
```python
# config.py pattern - environment variables with fallbacks
SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-key'
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
```

## 🎯 Role-Based Access Patterns

## 🎯 Role-Based Access Patterns

### Route Protection
```python
def shopkeeper_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
```

### Foreign Key Query Patterns
```python
# WRONG: Using user_id where shopkeeper_id is expected
# bills.shopkeeper_id -> shopkeepers.shopkeeper_id
query = Bill.query.filter_by(shopkeeper_id=shopkeeper.user_id)  # ❌

# CORRECT: Use shopkeeper.shopkeeper_id for bill/product queries
query = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)  # ✅

# CORRECT: Use shopkeeper.user_id for customer/ledger queries
# customers.shopkeeper_id -> users.user_id
customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id)  # ✅
```

### Context Processors
```python
# CA blueprint injects pending requests globally
@ca_bp.app_context_processor  
def inject_ca_pending_requests():
    return {'ca_pending_requests': get_ca_pending_requests()}
```

### User Loading
```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # In auth/routes.py
```

## 💡 Business Logic Patterns

### Bill Generation System
- **Dual product support**: Products from inventory + custom products per bill
- **GST calculation**: Automatic GST computation based on product HSN codes
- **Payment tracking**: `payment_status` enum with partial payment support
- **Stock management**: Automatic inventory deduction on bill creation

### Customer Ledger (Khata) System
```python
# Transaction types: 'PURCHASE', 'PAYMENT', 'ADJUSTMENT'
# Balance calculation: Running balance maintained per transaction
# Credit sales: Debit entries for purchases, Credit entries for payments
```

### Payment Field Handling
```python
# Bills use single consistent payment field set
bill = Bill(
    # ... other fields ...
    paid_amount=paid_amount,      # Amount paid
    due_amount=due_amount         # Amount due
)
```

### Connection Workflow
1. Shopkeeper requests connection to CA (`ShopConnection` model)
2. CA approves/rejects via dashboard
3. Approved connections become `CAConnection` records
4. CA can delegate to employees via `EmployeeClient` mapping

### File Upload Conventions
- **Shopkeeper docs**: `uploads/shopkeeper_{id}_{document_type}.{ext}`
- **CA uploads**: `ca_upload/{filename}` (direct storage)
- **Allowed formats**: PDF, JPG, PNG for documents

## 🔍 Code Quality Patterns

### Database Query Optimization
```python
# Use joinedload for related data
Bill.query.options(joinedload(Bill.bill_items)).filter_by(shopkeeper_id=id)

# Date filtering patterns
today = datetime.date.today()
bills_today = Bill.query.filter_by(shopkeeper_id=shopkeeper_id, bill_date=today).all()
```

### Error Handling
- **Flash messaging**: Consistent use of Flask flash messages for user feedback
- **Database rollback**: Transaction rollback on errors with user notification
- **File validation**: File type and size validation before uploads

### Form Handling
- **WTForms integration**: All forms use WTForms with CSRF protection
- **Validation patterns**: Email validation, length constraints, custom validators
- **Dynamic choices**: SelectField choices populated from database queries

## 🚀 Deployment Configuration

### Docker Support
- **Base image**: `python:3.10-slim`
- **ODBC drivers**: Microsoft ODBC Driver 18 for SQL Server (legacy compatibility)
- **Environment variables**: Database connection, Flask configuration
- **Port**: Standard Flask development port 5000

### Production Considerations
- **Session security**: Secure cookies enabled in production mode
- **Database pooling**: SQLAlchemy pool configuration for concurrent users  
- **File permissions**: Upload directory permissions for document storage
- **WSGI server**: Gunicorn configuration for production deployment

## 📋 Common Development Tasks

### Adding New Models
1. Define in `app/models.py` with proper relationships
2. Use consistent naming: plural table names, singular model names
3. Include `created_at`, `updated_at` timestamps where relevant
4. Add proper foreign key constraints with cascade behavior

### New Route Implementation
1. Add to appropriate blueprint (`auth/`, `shopkeeper/`, `ca/`, `api/`)
2. Implement role-based access control decorators
3. Follow template naming convention: `{blueprint}/{action}.html`
4. Add form classes to `app/forms.py` for complex forms

### Database Schema Changes
1. Update `app/models.py` for SQLAlchemy definitions
2. Update `schema.sql` for fresh installations
3. Consider migration strategy for existing data
4. Test with both MySQL and potential SQL Server compatibility

### File Upload Features
1. Use `werkzeug.utils.secure_filename()` for file naming
2. Validate file types and sizes before processing
3. Store file paths in database, actual files in static directories
4. Implement proper error handling for upload failures

## 🚀 AI Development Guidelines

### Quick Start Commands
```bash
# Start development server (auto-creates tables)
python run.py

# Test app initialization
python -c "from app import create_app; app = create_app(); print('✅ App ready')"

# Check database connectivity
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    try:
        db.engine.execute('SELECT 1')
        print('✅ Database connected')
    except Exception as e:
        print(f'❌ DB Error: {e}')
"

# Validate models
python -c "
from app import create_app
from app.models import *
app = create_app()
with app.app_context():
    db.create_all()
    print('✅ Models validated')
"
```

### Critical Patterns for AI Agents

#### 1. **Foreign Key Navigation** (Most Important)
```python
# ❌ WRONG - Causes constraint violations
shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.user_id)  # WRONG!

# ✅ CORRECT - Use proper foreign key relationships
shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)  # shopkeeper.shopkeeper_id
customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id)  # shopkeeper.user_id
```

#### 2. **Blueprint Route Structure**
```python
# Always include these decorators for protected routes
@shopkeeper_bp.route('/dashboard')
@login_required
@shopkeeper_required  # Role-specific decorator
def dashboard():
    # Always verify shopkeeper exists
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    if not shopkeeper:
        return redirect(url_for('auth.login'))
    # Use shopkeeper.shopkeeper_id for business queries
    bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
    return render_template('shopkeeper/dashboard.html', bills=bills)
```

#### 3. **Payment Field Consistency**
```python
# Bills use ONLY these fields (legacy fields removed)
bill = Bill(
    paid_amount=paid_amount,  # Amount paid
    due_amount=due_amount     # Amount due
)
# Display in templates: bill.paid_amount, bill.due_amount
```

#### 4. **Database Transaction Safety**
```python
# Always use proper transaction handling
try:
    bill = Bill(...)
    db.session.add(bill)
    db.session.commit()  # Explicit commit
except Exception as e:
    db.session.rollback()  # Always rollback on error
    flash(f'Error: {str(e)}', 'danger')
```

#### 5. **Template Organization**
```django
{# Always extend role-specific base templates #}
{% extends 'shopkeeper/s_base.html' %}

{# Use consistent responsive classes #}
<div class="flex flex-col md:flex-row md:justify-between md:items-center">
    <h1 class="text-2xl md:text-3xl font-bold">Dashboard</h1>
</div>

{# Include CSRF protection #}
<form method="POST">
    {{ form.hidden_tag() }}
    <!-- form fields -->
</form>
```

### Common Pitfalls to Avoid
- **Foreign Key Confusion**: `shopkeeper.user_id` vs `shopkeeper.shopkeeper_id`
- **Payment Field Mixing**: Don't reference removed `amount_paid`/`amount_unpaid` fields
- **Missing Role Checks**: Always use `@shopkeeper_required`/`@ca_required` decorators
- **Template Path Errors**: Use `{role}/{action}.html` naming convention
- **Database Session Leaks**: Always commit or rollback transactions

### Integration Points
- **GST Calculations**: Use `Decimal` for precise money calculations
- **File Uploads**: Store in `app/static/uploads/` or `app/static/ca_upload/`
- **Customer Ledger**: Maintain running balance with debit/credit entries
- **Session Management**: Filesystem-based sessions in `flask_session/` directory

---

**Key Files to Reference**: `app/models.py` (data relationships), `app/config.py` (environment setup), `app/__init__.py` (blueprint structure), `run.py` (application entry point), `CUSTOMER_LEDGER_IMPLEMENTATION.md` (ledger system), `create_bill_architecture.md` (bill creation logic)
