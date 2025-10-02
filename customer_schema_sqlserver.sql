-- SQL Server compatible schema for customer management system
-- Run this script in your Azure SQL Server database

-- Create customers table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='customers' AND xtype='U')
BEGIN
    CREATE TABLE customers (
        customer_id INT IDENTITY(1,1) PRIMARY KEY,
        shop_id INT NOT NULL,
        name NVARCHAR(100) NOT NULL,
        phone NVARCHAR(20),
        email NVARCHAR(100),
        address NVARCHAR(500),
        gst_number NVARCHAR(20),
        balance DECIMAL(10,2) DEFAULT 0.00,
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (shop_id) REFERENCES users(user_id)
    );
END

-- Create customer_ledger table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='customer_ledger' AND xtype='U')
BEGIN
    CREATE TABLE customer_ledger (
        ledger_id INT IDENTITY(1,1) PRIMARY KEY,
        customer_id INT NOT NULL,
        transaction_type NVARCHAR(10) NOT NULL CHECK (transaction_type IN ('Debit', 'Credit')),
        amount DECIMAL(10,2) NOT NULL,
        description NVARCHAR(255),
        bill_id INT NULL,
        transaction_date DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
    );
END

-- Create trigger to update customer balance
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'trg_update_customer_balance')
BEGIN
    DROP TRIGGER trg_update_customer_balance;
END
GO

CREATE TRIGGER trg_update_customer_balance
ON customer_ledger
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE customers 
    SET balance = (
        SELECT ISNULL(SUM(CASE 
            WHEN transaction_type = 'Debit' THEN amount 
            WHEN transaction_type = 'Credit' THEN -amount 
            ELSE 0 
        END), 0)
        FROM customer_ledger 
        WHERE customer_id = customers.customer_id
    ),
    updated_at = GETDATE()
    WHERE customer_id IN (SELECT DISTINCT customer_id FROM inserted);
END
GO

-- Create view for customer summary
IF EXISTS (SELECT * FROM sys.views WHERE name = 'customer_summary')
BEGIN
    DROP VIEW customer_summary;
END
GO

CREATE VIEW customer_summary AS
SELECT 
    c.customer_id,
    c.name,
    c.phone,
    c.email,
    c.balance,
    COUNT(DISTINCT b.bill_id) as total_bills,
    ISNULL(SUM(b.total_amount), 0) as total_purchase,
    ISNULL(SUM(b.paid_amount), 0) as total_paid,
    ISNULL(SUM(b.due_amount), 0) as total_due
FROM customers c
LEFT JOIN bills b ON c.customer_id = b.customer_id
GROUP BY c.customer_id, c.name, c.phone, c.email, c.balance;
GO

-- Add foreign key constraint for bills table (if customers table exists)
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_bills_customer')
BEGIN
    ALTER TABLE bills ADD CONSTRAINT FK_bills_customer 
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id);
END

-- Insert sample data (optional)
-- Uncomment the following if you want to add sample customers

/*
INSERT INTO customers (shop_id, name, phone, email, address, balance) VALUES
(1, 'John Doe', '9876543210', 'john@example.com', '123 Main St', 0.00),
(1, 'Jane Smith', '9876543211', 'jane@example.com', '456 Oak Ave', 0.00),
(1, 'Bob Johnson', '9876543212', 'bob@example.com', '789 Pine Rd', 0.00);
*/

PRINT 'Customer management schema created successfully!';

-- Fix missing columns in bills table
-- Run this script in your SQL Server database (Azure SQL)

-- Check if columns exist and add them if they don't
-- SQL Server syntax for adding columns

-- Add customer_id column if it doesn't exist
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'bills' AND COLUMN_NAME = 'customer_id')
BEGIN
    ALTER TABLE bills ADD customer_id INT NULL;
END

-- Add payment_status column if it doesn't exist  
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'bills' AND COLUMN_NAME = 'payment_status')
BEGIN
    ALTER TABLE bills ADD payment_status NVARCHAR(20) DEFAULT 'Paid';
END

-- Add paid_amount column if it doesn't exist
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'bills' AND COLUMN_NAME = 'paid_amount')
BEGIN
    ALTER TABLE bills ADD paid_amount DECIMAL(10,2) DEFAULT 0.00;
END

-- Add due_amount column if it doesn't exist
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'bills' AND COLUMN_NAME = 'due_amount')
BEGIN
    ALTER TABLE bills ADD due_amount DECIMAL(10,2) DEFAULT 0.00;
END

-- Update existing bills to have proper paid_amount values
-- For existing bills, set paid_amount = total_amount (assuming they were all paid)
UPDATE bills 
SET paid_amount = total_amount, 
    due_amount = 0.00, 
    payment_status = 'Paid' 
WHERE paid_amount IS NULL OR paid_amount = 0;

-- Show the updated table structure
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'bills'
ORDER BY ORDINAL_POSITION;
