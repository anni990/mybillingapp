# SQL Server Trigger Fix for CustomerLedger

## Problem Summary
SQLAlchemy's default behavior uses OUTPUT clauses when inserting records, but SQL Server doesn't allow OUTPUT clauses on tables with enabled triggers. The `customer_ledger` table has a trigger that automatically updates the `customers.total_balance` field, causing conflicts.

## Quick Application Fix Applied

The following files have been updated to use `session.no_autoflush` when creating CustomerLedger entries:

### 1. app/shopkeeper/views/bills.py
- Lines 902-930: Added `with db.session.no_autoflush:` wrapper for purchase and payment ledger entries

### 2. app/shopkeeper/views/customers.py  
- Lines 251-267: Added `with db.session.no_autoflush:` wrapper for manual ledger entries

### 3. app/shopkeeper/services/customer_service.py
- Lines 109-125: Added `with db.session.no_autoflush:` wrapper for service-level ledger entries

## What this fixes:
- Prevents SQLAlchemy from using OUTPUT clauses during CustomerLedger inserts
- Allows the SQL Server trigger to function properly
- Maintains data integrity and balance calculations

## Alternative Database Fix
If you prefer to fix the database side instead, run the trigger update from `fix_trigger_output_conflict.sql`:

```sql
-- Drop the conflicting trigger
DROP TRIGGER tr_update_customer_balance;

-- Create a compatible version  
GO
CREATE TRIGGER tr_update_customer_balance
ON customer_ledger
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    WITH LatestBalance AS (
        SELECT customer_id, balance_amount,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY transaction_date DESC, ledger_id DESC) as rn
        FROM customer_ledger
        WHERE customer_id IN (SELECT DISTINCT customer_id FROM inserted)
    )
    UPDATE customers
    SET total_balance = lb.balance_amount, updated_date = GETDATE()
    FROM customers c
    INNER JOIN LatestBalance lb ON c.customer_id = lb.customer_id
    WHERE lb.rn = 1;
END;
GO
```

## Testing
1. Restart your Flask application
2. Try creating a bill with a customer 
3. The error should be resolved

## Notes
- The `no_autoflush` approach is safer for production as it doesn't require database changes
- Both fixes achieve the same result - preventing OUTPUT clause conflicts
- This is a common issue when migrating from MySQL/PostgreSQL to SQL Server with SQLAlchemy