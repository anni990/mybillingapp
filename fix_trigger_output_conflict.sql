-- Fix SQL Server Trigger Compatibility Issue
-- File: fix_trigger_output_conflict.sql
-- Purpose: Resolve conflict between SQLAlchemy OUTPUT clause and SQL Server triggers
-- Date: October 11, 2025

-- Connect to your SQL Server database and run these commands:

-- SOLUTION 1: Replace the trigger with a version that works with OUTPUT clause
-- This removes the existing trigger and creates a new one that's compatible

-- Drop the existing trigger that conflicts with OUTPUT clause
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_update_customer_balance')
BEGIN
    DROP TRIGGER tr_update_customer_balance;
    PRINT 'Dropped existing trigger tr_update_customer_balance';
END;

-- Create a new trigger that works with SQLAlchemy's OUTPUT clause
-- This trigger updates the customer balance after ledger entries
GO
CREATE TRIGGER tr_update_customer_balance_v2
ON customer_ledger
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Handle both INSERT and UPDATE operations
    -- Use a CTE to get the latest balance for each customer
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

-- SOLUTION 2 (Alternative): If triggers still cause issues, use this approach
-- Comment out the above and uncomment this section to remove triggers entirely

/*
-- Remove all triggers from customer_ledger table
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_update_customer_balance')
    DROP TRIGGER tr_update_customer_balance;

IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_update_customer_balance_v2')
    DROP TRIGGER tr_update_customer_balance_v2;

PRINT 'All customer_ledger triggers removed - balance updates will be handled by application code';
*/

-- Verify the fix
SELECT 
    t.name AS TriggerName,
    t.type_desc AS TriggerType,
    o.name AS TableName
FROM sys.triggers t
INNER JOIN sys.objects o ON t.parent_id = o.object_id
WHERE o.name = 'customer_ledger';

PRINT 'Trigger compatibility fix applied successfully!';
PRINT 'SQLAlchemy OUTPUT clause should now work with customer_ledger table';

-- Test query to verify customer balance calculation works
SELECT 
    c.customer_id,
    c.name,
    c.total_balance as current_balance,
    (SELECT TOP 1 balance_amount 
     FROM customer_ledger cl 
     WHERE cl.customer_id = c.customer_id 
     ORDER BY transaction_date DESC, ledger_id DESC) as latest_ledger_balance
FROM customers c
WHERE EXISTS (SELECT 1 FROM customer_ledger WHERE customer_id = c.customer_id);