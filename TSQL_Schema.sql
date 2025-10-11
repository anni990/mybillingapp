-- T-SQL Schema for MyBillingApp
-- SQL Server Database Creation Script
-- Generated from MySQL schema on October 11, 2025

-- Create Database (uncomment if needed)
-- CREATE DATABASE mybillingapp1;
-- GO
-- USE mybillingapp1;
-- GO

-- Table structure for table users
CREATE TABLE users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) NOT NULL,
    email NVARCHAR(100) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) NOT NULL CHECK (role IN ('shopkeeper', 'CA', 'employee')),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    plain_password NVARCHAR(255) NULL,
    walkthrough_completed BIT NOT NULL DEFAULT 0
);

-- Table structure for table shopkeepers
CREATE TABLE shopkeepers (
    shopkeeper_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    shop_name NVARCHAR(100) NOT NULL,
    domain NVARCHAR(50) NULL,
    address NVARCHAR(255) NULL,
    gst_number NVARCHAR(20) NULL,
    contact_number NVARCHAR(20) NULL,
    gst_doc_path NVARCHAR(255) NULL,
    pan_doc_path NVARCHAR(255) NULL,
    address_proof_path NVARCHAR(255) NULL,
    logo_path NVARCHAR(255) NULL,
    aadhaar_dl_path NVARCHAR(255) NULL,
    selfie_path NVARCHAR(255) NULL,
    gumasta_path NVARCHAR(255) NULL,
    udyam_path NVARCHAR(255) NULL,
    bank_statement_path NVARCHAR(255) NULL,
    is_verified BIT NOT NULL DEFAULT 0,
    bank_name NVARCHAR(100) NULL,
    account_number NVARCHAR(50) NULL,
    ifsc_code NVARCHAR(20) NULL,
    template_choice NVARCHAR(20) NOT NULL DEFAULT 'template2',
    city NVARCHAR(100) NULL,
    state NVARCHAR(100) NULL,
    pincode NVARCHAR(20) NULL,
    CONSTRAINT FK_shopkeepers_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Table structure for table chartered_accountants
CREATE TABLE chartered_accountants (
    ca_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    firm_name NVARCHAR(100) NOT NULL,
    area NVARCHAR(100) NULL,
    contact_number NVARCHAR(20) NULL,
    gst_number NVARCHAR(20) NULL,
    pan_number NVARCHAR(20) NULL,
    address NVARCHAR(255) NULL,
    city NVARCHAR(100) NULL,
    state NVARCHAR(100) NULL,
    pincode NVARCHAR(20) NULL,
    aadhaar_file NVARCHAR(255) NULL,
    pan_file NVARCHAR(255) NULL,
    icai_certificate_file NVARCHAR(255) NULL,
    cop_certificate_file NVARCHAR(255) NULL,
    gstin NVARCHAR(30) NULL,
    business_reg_file NVARCHAR(255) NULL,
    bank_details_file NVARCHAR(255) NULL,
    photo_file NVARCHAR(255) NULL,
    signature_file NVARCHAR(255) NULL,
    office_address_proof_file NVARCHAR(255) NULL,
    self_declaration_file NVARCHAR(255) NULL,
    about_me NVARCHAR(2000) NULL,
    CONSTRAINT FK_chartered_accountants_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Table structure for table ca_employees
CREATE TABLE ca_employees (
    employee_id INT IDENTITY(1,1) PRIMARY KEY,
    ca_id INT NOT NULL,
    user_id INT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) NOT NULL,
    CONSTRAINT FK_ca_employees_ca FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE CASCADE,
    CONSTRAINT FK_ca_employees_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE NO ACTION
);

-- Table structure for table customers
CREATE TABLE customers (
    customer_id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    name NVARCHAR(100) NOT NULL,
    phone NVARCHAR(15) NOT NULL,
    email NVARCHAR(100) NULL,
    address NVARCHAR(MAX) NULL,
    created_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    is_active BIT NOT NULL DEFAULT 1,
    total_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT FK_customers_user FOREIGN KEY (shopkeeper_id) REFERENCES users(user_id),
    CONSTRAINT UQ_customers_shopkeeper_phone UNIQUE (shopkeeper_id, phone)
);

-- Table structure for table products
CREATE TABLE products (
    product_id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    product_name NVARCHAR(100) NOT NULL,
    barcode NVARCHAR(50) NULL,
    price DECIMAL(10,2) NOT NULL,
    stock_qty INT NOT NULL DEFAULT 0,
    low_stock_threshold INT NOT NULL DEFAULT 0,
    gst_rate DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    hsn_code NVARCHAR(20) NULL,
    CONSTRAINT FK_products_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE
);

-- Table structure for table bills
CREATE TABLE bills (
    bill_id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    bill_number NVARCHAR(50) NOT NULL,
    customer_name NVARCHAR(100) NULL,
    customer_address NVARCHAR(255) NULL,
    customer_gstin NVARCHAR(20) NULL,
    customer_contact NVARCHAR(20) NULL,
    bill_date DATE NOT NULL,
    gst_type NVARCHAR(10) NOT NULL CHECK (gst_type IN ('GST', 'Non-GST')),
    total_amount DECIMAL(12,2) NOT NULL,
    payment_status NVARCHAR(20) NOT NULL DEFAULT 'Paid' CHECK (payment_status IN ('Paid', 'Unpaid', 'Partial')),
    pdf_file_path NVARCHAR(255) NULL,
    customer_id INT NULL,
    paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    due_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT FK_bills_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE,
    CONSTRAINT FK_bills_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Table structure for table bill_items
CREATE TABLE bill_items (
    bill_item_id INT IDENTITY(1,1) PRIMARY KEY,
    bill_id INT NOT NULL,
    product_id INT NULL,
    custom_product_name NVARCHAR(100) NULL,
    custom_gst_rate DECIMAL(5,2) NULL,
    custom_hsn_code NVARCHAR(20) NULL,
    quantity INT NOT NULL,
    price_per_unit DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    CONSTRAINT FK_bill_items_bill FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
    CONSTRAINT FK_bill_items_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE NO ACTION
);

-- Table structure for table customer_ledger
CREATE TABLE customer_ledger (
    ledger_id INT IDENTITY(1,1) PRIMARY KEY,
    customer_id INT NOT NULL,
    shopkeeper_id INT NOT NULL,
    transaction_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    invoice_no NVARCHAR(50) NULL,
    particulars NVARCHAR(255) NOT NULL,
    debit_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    credit_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    balance_amount DECIMAL(10,2) NOT NULL,
    transaction_type NVARCHAR(20) NOT NULL,
    reference_bill_id INT NULL,
    notes NVARCHAR(MAX) NULL,
    created_date DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_customer_ledger_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT FK_customer_ledger_user FOREIGN KEY (shopkeeper_id) REFERENCES users(user_id),
    CONSTRAINT FK_customer_ledger_bill FOREIGN KEY (reference_bill_id) REFERENCES bills(bill_id)
);

-- Table structure for table ca_connections
CREATE TABLE ca_connections (
    id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    ca_id INT NOT NULL,
    status NVARCHAR(10) NOT NULL DEFAULT 'rejected' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_ca_connections UNIQUE (shopkeeper_id, ca_id),
    CONSTRAINT FK_ca_connections_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE,
    CONSTRAINT FK_ca_connections_ca FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE NO ACTION
);

-- Table structure for table shop_connections
CREATE TABLE shop_connections (
    id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    ca_id INT NOT NULL,
    status NVARCHAR(10) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_shop_connections UNIQUE (shopkeeper_id, ca_id),
    CONSTRAINT FK_shop_connections_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE,
    CONSTRAINT FK_shop_connections_ca FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE NO ACTION
);

-- Table structure for table employee_clients
CREATE TABLE employee_clients (
    id INT IDENTITY(1,1) PRIMARY KEY,
    employee_id INT NOT NULL,
    shopkeeper_id INT NOT NULL,
    CONSTRAINT FK_employee_clients_employee FOREIGN KEY (employee_id) REFERENCES ca_employees(employee_id) ON DELETE CASCADE,
    CONSTRAINT FK_employee_clients_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE NO ACTION
);

-- Table structure for table gst_filing_status
CREATE TABLE gst_filing_status (
    id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    employee_id INT NULL,
    month NVARCHAR(7) NOT NULL,
    status NVARCHAR(10) NOT NULL DEFAULT 'Not Filed' CHECK (status IN ('Filed', 'Not Filed')),
    filed_at DATETIME2 NULL,
    CONSTRAINT FK_gst_filing_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE NO ACTION,
    CONSTRAINT FK_gst_filing_employee FOREIGN KEY (employee_id) REFERENCES ca_employees(employee_id) ON DELETE SET NULL
);

-- Table structure for table documents
CREATE TABLE documents (
    document_id INT IDENTITY(1,1) PRIMARY KEY,
    shopkeeper_id INT NULL,
    ca_id INT NULL,
    document_name NVARCHAR(100) NOT NULL,
    file_path NVARCHAR(255) NOT NULL,
    uploaded_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_documents_shopkeeper FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE NO ACTION,
    CONSTRAINT FK_documents_ca FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE NO ACTION
);

-- Create indexes for performance optimization
CREATE INDEX IX_shopkeepers_user_id ON shopkeepers(user_id);
CREATE INDEX IX_chartered_accountants_user_id ON chartered_accountants(user_id);
CREATE INDEX IX_ca_employees_ca_id ON ca_employees(ca_id);
CREATE INDEX IX_ca_employees_user_id ON ca_employees(user_id);
CREATE INDEX IX_customers_shopkeeper_phone ON customers(shopkeeper_id, phone);
CREATE INDEX IX_products_shopkeeper_id ON products(shopkeeper_id);
CREATE INDEX IX_bills_shopkeeper_id ON bills(shopkeeper_id);
CREATE INDEX IX_bills_customer_id ON bills(customer_id);
CREATE INDEX IX_bill_items_bill_id ON bill_items(bill_id);
CREATE INDEX IX_bill_items_product_id ON bill_items(product_id);
CREATE INDEX IX_customer_ledger_customer_id ON customer_ledger(customer_id);
CREATE INDEX IX_customer_ledger_shopkeeper_id ON customer_ledger(shopkeeper_id);
CREATE INDEX IX_customer_ledger_transaction_date ON customer_ledger(transaction_date);
CREATE INDEX IX_customer_ledger_reference_bill_id ON customer_ledger(reference_bill_id);
CREATE INDEX IX_employee_clients_employee_id ON employee_clients(employee_id);
CREATE INDEX IX_employee_clients_shopkeeper_id ON employee_clients(shopkeeper_id);
CREATE INDEX IX_gst_filing_shopkeeper_id ON gst_filing_status(shopkeeper_id);
CREATE INDEX IX_gst_filing_employee_id ON gst_filing_status(employee_id);
CREATE INDEX IX_documents_shopkeeper_id ON documents(shopkeeper_id);
CREATE INDEX IX_documents_ca_id ON documents(ca_id);

-- Create trigger to update customer balance when ledger entry is added
GO
CREATE TRIGGER tr_update_customer_balance
ON customer_ledger
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE customers 
    SET 
        total_balance = i.balance_amount,
        updated_date = GETDATE()
    FROM customers c
    INNER JOIN inserted i ON c.customer_id = i.customer_id;
END;
GO

-- Create trigger to update updated_at timestamp for customers
CREATE TRIGGER tr_customers_updated_date
ON customers
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE customers 
    SET updated_date = GETDATE()
    FROM customers c
    INNER JOIN inserted i ON c.customer_id = i.customer_id;
END;
GO

-- Create trigger to update updated_at timestamp for ca_connections
CREATE TRIGGER tr_ca_connections_updated_at
ON ca_connections
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE ca_connections 
    SET updated_at = GETDATE()
    FROM ca_connections c
    INNER JOIN inserted i ON c.id = i.id;
END;
GO

-- Create trigger to update updated_at timestamp for shop_connections
CREATE TRIGGER tr_shop_connections_updated_at
ON shop_connections
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE shop_connections 
    SET updated_at = GETDATE()
    FROM shop_connections c
    INNER JOIN inserted i ON c.id = i.id;
END;
GO

-- Create view for customer summary (equivalent to MySQL view)
CREATE VIEW v_customer_summary AS
SELECT 
    c.customer_id,
    c.shopkeeper_id,
    c.name,
    c.phone,
    c.email,
    c.address,
    c.total_balance,
    c.created_date,
    COUNT(cl.ledger_id) AS total_transactions,
    SUM(CASE WHEN cl.debit_amount > 0 THEN cl.debit_amount ELSE 0 END) AS total_purchases,
    SUM(CASE WHEN cl.credit_amount > 0 THEN cl.credit_amount ELSE 0 END) AS total_payments,
    MAX(cl.transaction_date) AS last_transaction_date,
    COUNT(b.bill_id) AS total_bills
FROM customers c
LEFT JOIN customer_ledger cl ON c.customer_id = cl.customer_id
LEFT JOIN bills b ON c.customer_id = b.customer_id
GROUP BY 
    c.customer_id,
    c.shopkeeper_id,
    c.name,
    c.phone,
    c.email,
    c.address,
    c.total_balance,
    c.created_date;
GO

-- Print completion message
PRINT 'MyBillingApp T-SQL Schema created successfully!';
PRINT 'Database tables, indexes, triggers, and views have been created.';
PRINT '';
PRINT 'Key differences from MySQL:';
PRINT '- IDENTITY columns instead of AUTO_INCREMENT';
PRINT '- NVARCHAR instead of VARCHAR for Unicode support';
PRINT '- DATETIME2 instead of TIMESTAMP for better precision';
PRINT '- BIT instead of TINYINT for boolean values';
PRINT '- CHECK constraints instead of ENUM types';
PRINT '- Explicit trigger creation for timestamp updates';
PRINT '';
PRINT 'CRITICAL FIXES APPLIED based on code analysis:';
PRINT '1. Added missing about_me field to chartered_accountants table';
PRINT '2. Added missing walkthrough_completed field to users table';
PRINT '3. Fixed payment_status field size from NVARCHAR(10) to NVARCHAR(20)';
PRINT '4. Added missing foreign key constraints to ca_connections table';
PRINT '5. Verified all enum values match application code';
PRINT '6. Ensured all nullable/non-nullable fields match models exactly';
PRINT '7. FIXED CASCADE CONFLICTS: Adjusted FK constraints to prevent circular cascades';
PRINT '';
PRINT 'CASCADE STRATEGY APPLIED:';
PRINT '- Primary cascades: users -> shopkeepers/chartered_accountants -> their direct children';
PRINT '- Secondary relations: Use NO ACTION or SET NULL to prevent cycles';
PRINT '- Business logic: Application handles cleanup for non-cascading relationships';
PRINT '';
PRINT 'Remember to:';
PRINT '1. Create the database first if it does not exist';
PRINT '2. Adjust connection strings in your application for SQL Server';
PRINT '3. Update any application code that relies on MySQL-specific features';
PRINT '4. Test payment_status values: Paid, Unpaid, Partial';
PRINT '5. Verify foreign key relationships work correctly with your Flask models';