# MyBillingApp - AI Developer Guide

## 🏗️ Architecture Overview

MyBillingApp is a **multi-tenant Flask ERP system** connecting Shopkeepers, Chartered Accountants (CAs), and CA Employees in a billing and GST management ecosystem. The app uses **modular blueprint architecture** with role-based access control.

**Core Business Flow:**
- **Shopkeepers**: Create bills, manage products/inventory, customer ledgers (khata system), connect with CAs
- **CAs**: Manage multiple shopkeeper clients, delegate to employees, track GST filing status
- **CA Employees**: Handle assigned shopkeeper accounts via delegation
- **Connection System**: Approval-based relationships between shopkeepers and CAs

## 🚨 Critical Foreign Key Patterns (Most Important!)

**Different tables use different foreign key references to the same shopkeeper:**

```python
# ✅ CORRECT - Use shopkeeper.shopkeeper_id for:
bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
ca_connections = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)

# ✅ CORRECT - Use shopkeeper.user_id for:
customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id)
ledger = CustomerLedger.query.filter_by(shopkeeper_id=shopkeeper.user_id)

# ❌ WRONG - This will cause foreign key constraint violations:
bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.user_id)  # WRONG!
customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)  # WRONG!
```

**Why this matters:** `customers.shopkeeper_id` → `users.user_id`, but `bills.shopkeeper_id` → `shopkeepers.shopkeeper_id`

## 🧩 Modular Blueprint Structure

**Blueprint Organization:** Each role has organized view modules in `app/{role}/views/` with route registration pattern:

```python
# app/shopkeeper/views/dashboard.py
def register_routes(bp):
    @bp.route('/dashboard')
    @login_required
    @shopkeeper_required
    def dashboard():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            return redirect(url_for('auth.login'))
        
        # Use correct foreign key!
        bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
        return render_template('shopkeeper/dashboard.html', bills=bills)

# app/shopkeeper/__init__.py
from .views import dashboard, bills, products, reports, customers, profile, ca_connections
dashboard.register_routes(shopkeeper_bp)
bills.register_routes(shopkeeper_bp)
```

**Template Convention:** `{blueprint}/{action}.html` (e.g., `shopkeeper/dashboard.html`, `ca/clients.html`)

## 💾 Data & Business Logic

**Payment Fields:** Bills use `paid_amount`/`due_amount` (legacy `amount_paid`/`amount_unpaid` removed)

**Customer Ledger System (Khata):**
```python
# Transaction types: 'PURCHASE', 'PAYMENT', 'ADJUSTMENT'
def create_ledger_entry(customer_id, transaction_type, debit_amount, credit_amount):
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

**GST Calculations:** Use `Decimal` for money math: `Decimal(str(price)) * Decimal(str(gst_rate)) / Decimal('100')`

## 🎨 Frontend Patterns

**Responsive Design:** Dual desktop/mobile views with Tailwind classes:
```html
<div class="hidden lg:block"><!-- Desktop table --></div>
<div class="lg:hidden"><!-- Mobile cards --></div>
```

**Modal System:** Blur-only backgrounds (no black overlays):
```html
<div class="fixed inset-0 backdrop-blur-sm hidden flex items-center justify-center z-50">
    <div class="bg-white rounded-xl shadow-2xl p-6 max-w-md w-full mx-4">
        <!-- Modal content -->
    </div>
</div>
```

**Dynamic Search:** 300ms debounced search with product suggestions in `create_bill.js`

**Icons:** Feather icons with `feather.replace()` initialization

## 🚀 Development Workflow

**Start development:**
```powershell
python run.py  # Auto-creates tables, runs debug mode
```

**Quick diagnostics:**
```powershell
# Test app
python -c "from app import create_app; app = create_app(); print('✅ App ready')"

# Check DB connection
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.session.execute(db.text('SELECT 1')); print('✅ Connected')"
```

**Database:** MySQL with PyMySQL driver. Session storage in `flask_session/` directory.

## 🔧 Critical Development Rules

1. **Always use role decorators:** `@login_required` + `@shopkeeper_required`/`@ca_required`
2. **Template naming:** Extend role-specific base templates (`shopkeeper/s_base.html`, `ca/ca_base.html`)
3. **Transaction safety:** Always commit or rollback database transactions explicitly
4. **File uploads:** Store in `app/static/uploads/` (shopkeeper) or `app/static/ca_upload/` (CA)
5. **Error handling:** Use Flask flash messages, not browser alerts

## 📁 Key Files

- `app/models.py` - Database relationships and foreign key patterns
- `app/{role}/views/` - Modular route organization  
- `app/config.py` - Environment and database configuration
- `run.py` - Application entry point with auto table creation
- `Complete Schema.sql` - Full database schema reference
- `temp/create_bill_workflow.md` - **Complete bill creation workflow with Mermaid diagrams**
