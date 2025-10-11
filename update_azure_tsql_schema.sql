-- Azure T-SQL Schema Update Commands
-- File: update_azure_tsql_schema.sql
-- Purpose: Update existing Azure SQL Server database with missing fields and fix cascade conflicts
-- Date: October 11, 2025
-- 
-- Run these commands on your existing Azure SQL Server database

-- Connect to your Azure SQL Database and run these commands:

-- 1. Add missing walkthrough_completed field to users table
ALTER TABLE users 
ADD walkthrough_completed BIT NOT NULL DEFAULT 0;

-- 2. Add missing about_me field to chartered_accountants table  
ALTER TABLE chartered_accountants 
ADD about_me NVARCHAR(2000) NULL;

-- 3. Fix cascade conflicts (run only if you encounter foreign key errors during schema deployment)
-- These commands fix circular cascade paths that SQL Server doesn't allow

-- Fix CAEmployee.user_id cascade conflict
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ca_employees_user')
BEGIN
    ALTER TABLE ca_employees DROP CONSTRAINT FK_ca_employees_user;
    ALTER TABLE ca_employees 
    ADD CONSTRAINT FK_ca_employees_user 
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE NO ACTION;
    PRINT 'Fixed ca_employees.user_id cascade conflict';
END;

-- Fix BillItem.product_id cascade conflict  
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_bill_items_product')
BEGIN
    ALTER TABLE bill_items DROP CONSTRAINT FK_bill_items_product;
    ALTER TABLE bill_items 
    ADD CONSTRAINT FK_bill_items_product 
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE NO ACTION;
    PRINT 'Fixed bill_items.product_id cascade conflict';
END;

-- Fix EmployeeClient.shopkeeper_id cascade conflict
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_employee_clients_shopkeeper')
BEGIN
    ALTER TABLE employee_clients DROP CONSTRAINT FK_employee_clients_shopkeeper;
    ALTER TABLE employee_clients 
    ADD CONSTRAINT FK_employee_clients_shopkeeper 
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE NO ACTION;
    PRINT 'Fixed employee_clients.shopkeeper_id cascade conflict';
END;

-- Fix CAConnection.ca_id cascade conflict
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_ca_connections_ca')
BEGIN
    ALTER TABLE ca_connections DROP CONSTRAINT FK_ca_connections_ca;
    ALTER TABLE ca_connections 
    ADD CONSTRAINT FK_ca_connections_ca 
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE NO ACTION;
    PRINT 'Fixed ca_connections.ca_id cascade conflict';
END;

-- Fix ShopConnection.ca_id cascade conflict
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_shop_connections_ca')
BEGIN
    ALTER TABLE shop_connections DROP CONSTRAINT FK_shop_connections_ca;
    ALTER TABLE shop_connections 
    ADD CONSTRAINT FK_shop_connections_ca 
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE NO ACTION;
    PRINT 'Fixed shop_connections.ca_id cascade conflict';
END;

-- Fix Documents table cascade conflicts
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_documents_shopkeeper')
BEGIN
    ALTER TABLE documents DROP CONSTRAINT FK_documents_shopkeeper;
    ALTER TABLE documents 
    ADD CONSTRAINT FK_documents_shopkeeper 
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE NO ACTION;
    PRINT 'Fixed documents.shopkeeper_id cascade conflict';
END;

IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_documents_ca')
BEGIN
    ALTER TABLE documents DROP CONSTRAINT FK_documents_ca;
    ALTER TABLE documents 
    ADD CONSTRAINT FK_documents_ca 
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE NO ACTION;
    PRINT 'Fixed documents.ca_id cascade conflict';
END;

-- Fix GSTFilingStatus cascade conflicts
IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_gst_filing_shopkeeper')
BEGIN
    ALTER TABLE gst_filing_status DROP CONSTRAINT FK_gst_filing_shopkeeper;
    ALTER TABLE gst_filing_status 
    ADD CONSTRAINT FK_gst_filing_shopkeeper 
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE NO ACTION;
    PRINT 'Fixed gst_filing_status.shopkeeper_id cascade conflict';
END;

IF EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_gst_filing_employee')
BEGIN
    ALTER TABLE gst_filing_status DROP CONSTRAINT FK_gst_filing_employee;
    ALTER TABLE gst_filing_status 
    ADD CONSTRAINT FK_gst_filing_employee 
    FOREIGN KEY (employee_id) REFERENCES ca_employees(employee_id) ON DELETE SET NULL;
    PRINT 'Fixed gst_filing_status.employee_id cascade conflict';
END;

-- Fix Trigger OUTPUT Conflict (SQLAlchemy compatibility issue)
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_update_customer_balance')
BEGIN
    DROP TRIGGER tr_update_customer_balance;
    PRINT 'Dropped existing trigger that conflicts with SQLAlchemy OUTPUT clause';
END;

-- Create compatible trigger for customer balance updates
GO
CREATE TRIGGER tr_update_customer_balance
ON customer_ledger
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Use CTE to handle multiple inserts and get latest balance per customer
    WITH LatestBalance AS (
        SELECT 
            customer_id,
            balance_amount,
            ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY transaction_date DESC, ledger_id DESC) as rn
        FROM customer_ledger cl
        WHERE cl.customer_id IN (SELECT DISTINCT customer_id FROM inserted)
    )
    UPDATE customers 
    SET 
        total_balance = lb.balance_amount,
        updated_date = GETDATE()
    FROM customers c
    INNER JOIN LatestBalance lb ON c.customer_id = lb.customer_id
    WHERE lb.rn = 1;
END;
GO

-- 4. Verify the updates
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE (TABLE_NAME = 'users' AND COLUMN_NAME = 'walkthrough_completed')
   OR (TABLE_NAME = 'chartered_accountants' AND COLUMN_NAME = 'about_me')
ORDER BY TABLE_NAME, COLUMN_NAME;

-- 5. Optional: Update existing records if needed
-- Uncomment and modify these queries as needed:

-- Set walkthrough_completed to 1 for existing users who should skip the walkthrough
-- UPDATE users SET walkthrough_completed = 1 WHERE role = 'CA' OR role = 'employee';

-- Add default about_me text for existing CAs who don't have this field
-- UPDATE chartered_accountants 
-- SET about_me = 'Professional chartered accountant providing comprehensive financial services.' 
-- WHERE about_me IS NULL;

PRINT 'Azure SQL Database schema update completed successfully!';
PRINT 'Fields added: users.walkthrough_completed, chartered_accountants.about_me';
PRINT 'Cascade conflicts resolved for SQL Server compatibility';
PRINT 'Trigger OUTPUT conflict fixed for SQLAlchemy compatibility';
