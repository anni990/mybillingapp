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
```powershell
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

# Install dependencies
pip install -r requirements.txt

# Check customer ledger system
python -c "
from app import create_app, db
from app.models import Customer, CustomerLedger
app = create_app()
with app.app_context():
    customers = Customer.query.limit(3).all()
    for c in customers:
        print(f'Customer {c.name}: Balance={c.total_balance}')
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

// CSRF Token Management
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// API Error Handling Pattern
fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(data)
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        showSuccess(data.message);
        // Handle success
    } else {
        showError(data.message);
    }
})
.catch(error => {
    showError('An error occurred. Please try again.');
});
```

### Tailwind CSS Conventions
```html
<!-- Responsive Grid Patterns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div class="bg-white rounded-lg shadow-md p-6">Content</div>
</div>

<!-- Button Patterns -->
<button class="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors">
    Primary Action
</button>

<button class="bg-gray-300 hover:bg-gray-400 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors">
    Secondary Action
</button>

<!-- Form Input Patterns -->
<input type="text" 
       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
       placeholder="Enter value...">

<!-- Modal Backdrop Styling -->
<div class="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm hidden flex items-center justify-center z-50">
    <div class="bg-white p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
        <!-- Modal content -->
    </div>
</div>
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

{# Conditional content rendering #}
{% if bills %}
    {% for bill in bills %}
        <div class="bill-item">{{ bill.bill_number }}</div>
    {% endfor %}
{% else %}
    <div class="text-gray-500 text-center py-8">No bills found</div>
{% endif %}
```

### Icon Integration (Feather Icons)
```html
<!-- Standard icon usage -->
<i data-feather="edit-2" class="w-4 h-4"></i>
<i data-feather="trash-2" class="w-4 h-4 text-red-500"></i>
<i data-feather="plus" class="w-5 h-5"></i>

<!-- Initialize Feather icons -->
<script>
    // Include in all templates with icons
    feather.replace();
</script>
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
- **Foreign Key Distinctions**: 
  - `customers.shopkeeper_id` → `users.user_id` (customer belongs to user account)
  - `bills.shopkeeper_id` → `shopkeepers.shopkeeper_id` (bill belongs to shop profile)
  - `products.shopkeeper_id` → `shopkeepers.shopkeeper_id` (product belongs to shop profile)
  - `ca_connections.shopkeeper_id` → `shopkeepers.shopkeeper_id` (connection between shop profiles)
  - `customer_ledger.shopkeeper_id` → `users.user_id` (ledger belongs to user account)
- **Payment Field Standardization**: Bills use single consistent field set (`paid_amount`/`due_amount`)
- **Soft cascade deletes**: Use `ondelete='CASCADE'` on foreign keys
- **Enum fields**: `role`, `gst_type`, `payment_status`, `transaction_type`
- **Decimal precision**: `db.Numeric(10,2)` for money fields, `db.Numeric(12,2)` for totals
- **MySQL migration**: Connection string uses `pymysql` driver, but ODBC dependencies remain in Dockerfile

### Schema Evolution
- Current schema: `Complete Schema.sql` (MySQL/MariaDB with full table definitions)
- Customer ledger system added via `Docx/CUSTOMER_LEDGER_IMPLEMENTATION.md`
- GST filing status tracking for compliance management
- Dual payment field support: `paid_amount`/`due_amount` (current) alongside legacy compatibility

### Critical Foreign Key Reference Patterns
```python
# ⚠️ CRITICAL: Different tables use different foreign key references to Shopkeeper

# For Bills, Products, CA Connections, Shop Connections:
# Use shopkeeper.shopkeeper_id (references shopkeepers table primary key)
bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
ca_connections = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)

# For Customers, Customer Ledger:
# Use shopkeeper.user_id (references users table primary key)
customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id)
ledger = CustomerLedger.query.filter_by(shopkeeper_id=shopkeeper.user_id)

# Model definitions that cause this pattern:
# customers.shopkeeper_id -> ForeignKey('users.user_id')
# customer_ledger.shopkeeper_id -> ForeignKey('users.user_id')
# bills.shopkeeper_id -> ForeignKey('shopkeepers.shopkeeper_id')
# products.shopkeeper_id -> ForeignKey('shopkeepers.shopkeeper_id')
```

### Current Status (Updated 2025-10-02)
- **✅ Foreign Key Issues Resolved**: All database queries now use correct foreign key references
- **✅ Payment Fields Migration Complete**: Bills table now uses single consistent field set (`paid_amount`/`due_amount`)
- **✅ Schema Compliance**: Database schema matches production schema with all required columns and constraints
- **✅ Customer Ledger System**: Full khata (credit/debit) system implemented with running balance tracking
- **✅ Multi-Database Support**: Active MySQL with PyMySQL driver, SQL Server compatibility maintained

## 🔧 Critical Fixes Applied

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

## 📁 File Organization

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
├── shopkeeper/
│   ├── routes.py          # Shopkeeper functionality (1677 lines) - legacy
│   ├── views/             # Modular view organization
│   │   ├── bills.py       # Bill management endpoints
│   │   ├── customers.py   # Customer CRUD operations
│   │   ├── dashboard.py   # Dashboard and analytics
│   │   ├── products.py    # Product and inventory
│   │   └── reports.py     # Sales and GST reports
│   └── services/          # Business logic layer
│       ├── bill_service.py     # Bill processing logic
│       ├── customer_service.py # Customer management logic
│       └── report_service.py   # Report generation logic
├── ca/
│   ├── routes.py          # CA functionality (1059 lines) - legacy
│   └── views/             # Modular CA view organization
│       ├── bills.py       # Client bill management
│       ├── clients.py     # Client relationship management
│       ├── connections.py # CA-Shopkeeper connections
│       ├── dashboard.py   # CA dashboard analytics
│       ├── employees.py   # Employee management
│       └── reports.py     # CA reporting and GST filing
└── api/routes.py         # API endpoints
```

### Static Assets
- **CSS**: `app/static/css/tailwind.css` (Tailwind CSS framework)
- **JavaScript**: `app/static/js/` (dashboard.js, create_bill.js, sales_reports.js, notifications.js)
- **File Uploads**: `app/static/uploads/` (shopkeeper docs), `app/static/ca_upload/` (CA docs)
- **Images**: `app/static/images/` (login, dashboard, CA assets)

### Template Organization
```
app/templates/
├── auth/                  # Authentication templates
│   ├── login.html        # User login interface
│   └── register.html     # User registration
├── ca/                   # CA role templates
│   ├── ca_base.html      # CA base template with navigation
│   ├── dashboard.html    # CA dashboard with client overview
│   ├── client_*.html     # Client management interfaces
│   └── employee_*.html   # Employee management
├── shopkeeper/           # Shopkeeper role templates
│   ├── s_base.html       # Shopkeeper base template
│   ├── dashboard.html    # Shopkeeper dashboard
│   ├── manage_bills.html # Bill CRUD with custom modals
│   ├── customer_*.html   # Customer management with ledger
│   └── products_*.html   # Product and inventory management
└── home/                 # Public templates
    ├── index.html        # Landing page
    └── about.html        # About page
```

### Template Patterns
- **Base templates**: `*_base.html` files in each role directory with role-specific navigation
- **Form templates**: Consistent form structure across roles with CSRF protection
- **Dashboard templates**: Role-specific dashboards with similar responsive layouts
- **Modal Integration**: Custom confirmation and input modals replacing browser dialogs

## 🔧 Development Workflow

### Running the Application
```powershell
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

## 🎨 UI/UX Patterns & Custom Modal System

### Custom Modal Architecture (Latest Implementation)
```html
<!-- Confirmation Modal Template -->
<div id="delete-confirmation-modal" class="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm hidden flex items-center justify-center z-50">
    <div class="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full mx-4">
        <h3 class="text-lg font-semibold mb-4">Confirm Deletion</h3>
        <p class="text-gray-600 mb-6">Are you sure you want to delete this bill? This action cannot be undone.</p>
        <div class="flex justify-end space-x-3">
            <button onclick="closeDeleteModal()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded">Cancel</button>
            <button onclick="confirmDelete()" class="px-4 py-2 bg-red-500 text-white rounded">Delete</button>
        </div>
    </div>
</div>
```

### Toast Notification System
```javascript
// Custom notification functions (replaces browser alerts)
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full`;
    
    if (type === 'success') {
        notification.className += ' bg-green-500 text-white';
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                </svg>
                <span>${message}</span>
            </div>`;
    } else {
        notification.className += ' bg-red-500 text-white';
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                </svg>
                <span>${message}</span>
            </div>`;
    }
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 100);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 4000);
}
```

### Modal Interaction Patterns
```javascript
// Standard modal opening/closing
function openDeleteModal(billId, billNumber) {
    currentBillId = billId;
    document.getElementById('bill-number-span').textContent = billNumber;
    document.getElementById('delete-confirmation-modal').classList.remove('hidden');
}

function closeDeleteModal() {
    document.getElementById('delete-confirmation-modal').classList.add('hidden');
    currentBillId = null;
}

// AJAX deletion with custom feedback
function confirmDelete() {
    if (!currentBillId) return;
    
    fetch(`/shopkeeper/delete_bill/${currentBillId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        closeDeleteModal();
        if (data.success) {
            showSuccess(data.message);
            setTimeout(() => location.reload(), 1000);
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        closeDeleteModal();
        showError('Error deleting bill. Please try again.');
    });
}
```

### Browser Notification Migration Strategy
**CRITICAL**: Replace ALL browser-based notifications with custom modals:
- `confirm()` → Custom confirmation modals with backdrop-blur
- `alert()` → Toast notification system with auto-dismiss
- `prompt()` → Custom input modals with form validation

**Files requiring migration**:
- `products_stock.html` (4 instances)
- `customer_management.html` (existing modals need standardization)
- `create_bill.html` (browser alerts)
- `customer_ledger.html` (browser alerts)
- `ca_marketplace.html` (browser alerts)
- `employee_profile.html` (browser alerts)

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
- **AJAX Error Handling**: JSON responses with success/error status and user-friendly messages

### Form Handling
- **WTForms integration**: All forms use WTForms with CSRF protection
- **Validation patterns**: Email validation, length constraints, custom validators
- **Dynamic choices**: SelectField choices populated from database queries
- **CSRF Token Management**: Include CSRF tokens in AJAX requests

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
```powershell
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
        result = db.session.execute(db.text('SELECT 1'))
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

# Environment setup
cp .env.example .env  # Copy and configure environment variables
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

**Key Files to Reference**: `app/models.py` (data relationships), `app/config.py` (environment setup), `app/__init__.py` (blueprint structure), `run.py` (application entry point), `Docx/CUSTOMER_LEDGER_IMPLEMENTATION.md` (ledger system), `Complete Schema.sql` (database structure)
