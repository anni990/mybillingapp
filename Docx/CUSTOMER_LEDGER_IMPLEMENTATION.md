# Customer Management & Ledger System Implementation Guide

## Overview
This implementation adds comprehensive customer management and ledger (khata) functionality to the MyBillingApp shopkeeper section. The system allows shopkeepers to manage customer relationships, track credit sales, and maintain detailed transaction ledgers.

## 🗄️ Database Schema Changes

### 1. New Tables Created

#### `customers` Table
```sql
CREATE TABLE customers (
    customer_id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    phone NVARCHAR(15) NOT NULL,
    email NVARCHAR(100) NULL,
    address NVARCHAR(255) NULL,
    created_date DATETIME DEFAULT GETDATE(),
    updated_date DATETIME DEFAULT GETDATE(),
    is_active BIT DEFAULT 1,
    total_balance DECIMAL(10,2) DEFAULT 0.00,
    FOREIGN KEY (shopkeeper_id) REFERENCES users(user_id),
    UNIQUE(shopkeeper_id, phone)
);
```

#### `customer_ledger` Table
```sql
CREATE TABLE customer_ledger (
    ledger_id INT IDENTITY(1,1) PRIMARY KEY,
    customer_id INT NOT NULL,
    shopkeeper_id INT NOT NULL,
    transaction_date DATETIME DEFAULT GETDATE(),
    invoice_no NVARCHAR(50) NULL,
    particulars NVARCHAR(255) NOT NULL,
    debit_amount DECIMAL(10,2) DEFAULT 0.00,
    credit_amount DECIMAL(10,2) DEFAULT 0.00,
    balance_amount DECIMAL(10,2) NOT NULL,
    transaction_type NVARCHAR(20) NOT NULL,
    reference_bill_id INT NULL,
    notes NVARCHAR(500) NULL,
    created_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (shopkeeper_id) REFERENCES users(user_id),
    FOREIGN KEY (reference_bill_id) REFERENCES bills(bill_id)
);
```

### 2. Updated Tables

#### `bills` Table Updates
```sql
ALTER TABLE bills ADD customer_id INT NULL;
ALTER TABLE bills ADD payment_status NVARCHAR(20) DEFAULT 'PAID';
ALTER TABLE bills ADD paid_amount DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE bills ADD due_amount DECIMAL(10,2) DEFAULT 0.00;
```

## 🔧 Backend Implementation

### 1. New Models Added
- `Customer` - Stores customer information and current balance
- `CustomerLedger` - Stores all debit/credit transactions
- Updated `Bill` model with customer references

### 2. New Routes Added

#### Customer Management Routes
- `GET /shopkeeper/customer_management` - Main customer management page
- `POST /shopkeeper/add_customer` - Add new customer
- `GET /shopkeeper/get_customer/<id>` - Get customer details
- `PUT /shopkeeper/update_customer/<id>` - Update customer
- `DELETE /shopkeeper/delete_customer/<id>` - Soft delete customer
- `GET /shopkeeper/get_customers_list` - Get customers for dropdown
- `GET /shopkeeper/export_customers` - Export customers to CSV

#### Ledger Management Routes
- `GET /shopkeeper/customer_ledger/<id>` - View customer ledger
- `POST /shopkeeper/add_ledger_entry/<id>` - Add ledger transaction

### 3. Updated Bill Creation
- Enhanced bill creation to support customer selection
- Automatic ledger entry creation for credit sales
- Payment status tracking (Paid/Partial/Unpaid)

## 🎨 Frontend Implementation

### 1. New Templates
- `customer_management.html` - Customer list and management
- `customer_ledger.html` - Individual customer ledger view

### 2. Updated Templates
- `create_bill.html` - Added customer selection and payment options

### 3. UI Features
- Customer search and filtering
- Responsive design for mobile/desktop
- Modern card-based layout
- Interactive modals for data entry

## 📊 Ledger System Logic

### Transaction Types
1. **PURCHASE** (Debit) - When customer buys goods on credit
2. **PAYMENT** (Credit) - When customer makes payment
3. **ADJUSTMENT** - Manual adjustments

### Balance Calculation
- **Balance = Total Debits - Total Credits**
- **Positive Balance** = Customer owes money (Dr)
- **Negative Balance** = Customer has advance/credit (Cr)

### Automatic Entries
- Purchase entries created automatically when bills are generated with Unpaid/Partial status
- Payment entries created when partial payments are made during bill creation

## 🚀 Key Features

### Customer Management
- ✅ Add/Edit/Delete customers
- ✅ Search and filter functionality
- ✅ Export customer data
- ✅ Customer statistics dashboard
- ✅ Duplicate phone number prevention

### Ledger System
- ✅ Complete transaction history
- ✅ Running balance calculation
- ✅ Debit/Credit entry management
- ✅ Bill reference linking
- ✅ Print functionality
- ✅ Mobile-responsive design

### Bill Integration
- ✅ Customer selection during bill creation
- ✅ Payment status options (Paid/Partial/Unpaid)
- ✅ Automatic ledger entry creation
- ✅ Guest customer support (no ledger tracking)

### Security Features
- ✅ Shopkeeper-specific data isolation
- ✅ Soft delete for data preservation
- ✅ Balance validation before customer deletion

## 📱 Usage Workflow

### 1. Customer Registration
1. Go to Customer Management section
2. Click "Add Customer"
3. Fill customer details (name, phone required)
4. Save customer

### 2. Creating Bills with Credit
1. Go to Create Bill
2. Select "Existing Customer" radio button
3. Choose customer from dropdown
4. Add products to bill
5. Select payment status:
   - **Paid** - Full payment received
   - **Partial** - Partial payment (specify amount)
   - **Unpaid** - Credit sale (no payment)
6. Generate bill

### 3. Managing Customer Ledger
1. Go to Customer Management
2. Click book icon next to customer
3. View complete transaction history
4. Add manual entries if needed:
   - Purchase entries (Debit)
   - Payment entries (Credit)
   - Adjustments

### 4. Tracking Payments
- Use customer ledger instead of bill payment updates
- Add payment entries to record when customers pay
- System automatically calculates running balance

## 🔄 Data Flow

### Bill Creation with Credit
1. Customer selects existing customer
2. Creates bill with Unpaid/Partial status
3. System automatically creates:
   - Purchase ledger entry (Debit)
   - Payment ledger entry (if partial payment)
4. Updates customer balance
5. Links bill to ledger entries

### Manual Payment Recording
1. Customer makes payment outside of bill creation
2. Shopkeeper adds payment entry to ledger
3. System updates customer balance
4. Transaction history maintained

## 🛡️ Business Rules

### Customer Management
- Phone numbers must be unique per shopkeeper
- Customers can only be soft deleted (is_active = false)
- Cannot delete customers with pending dues

### Ledger System
- All transactions maintain running balance
- Balance calculation: Previous Balance + Debit - Credit
- Automatic triggers update customer balance on ledger changes

### Bill Integration
- Guest customers: Bills created without customer_id (no ledger tracking)
- Registered customers: Bills linked to customer with optional ledger entries
- Payment status determines ledger entry creation

## 📈 Benefits

### For Shopkeepers
- Track customer credit/debt accurately
- Maintain complete transaction history
- Professional customer relationship management
- Easy payment tracking and follow-up

### For Business
- Improved cash flow management
- Better customer insights
- Reduced manual bookkeeping errors
- Professional ledger statements

## 🔧 Installation & Setup

### 1. Database Migration
Execute the SQL script: `customer_ledger_schema.sql`

### 2. Application Update
- Models updated in `models.py`
- Routes added to `shopkeeper/routes.py`
- Templates created/updated

### 3. Testing
1. Add some test customers
2. Create bills with different payment statuses
3. Verify ledger entries are created correctly
4. Test customer ledger functionality

## 📝 Notes

- Bill payment update functionality has been disabled in favor of ledger-based payment tracking
- System maintains data integrity with foreign key constraints
- All customer data is isolated per shopkeeper for security
- Responsive design ensures mobile compatibility

This implementation provides a complete customer relationship and credit management system that aligns with traditional Indian business practices while offering modern digital convenience.
