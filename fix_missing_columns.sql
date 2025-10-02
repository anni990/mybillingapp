-- Migration script to add missing columns to match production schema
-- Run this against your MySQL database to add the missing fields

-- Add missing legacy payment columns to bills table
ALTER TABLE bills
ADD COLUMN amount_paid DECIMAL(12,2) DEFAULT 0.00 AFTER payment_status,
ADD COLUMN amount_unpaid DECIMAL(12,2) DEFAULT 0.00 AFTER amount_paid;

-- Update existing bills to set legacy payment values from current fields
UPDATE bills SET
    amount_paid = paid_amount,
    amount_unpaid = due_amount
WHERE amount_paid = 0 AND amount_unpaid = 0;

-- Ensure customers table has total_balance column
ALTER TABLE customers
ADD COLUMN total_balance DECIMAL(10,2) DEFAULT 0.00 AFTER is_active;

-- Initialize total_balance for existing customers
UPDATE customers SET total_balance = 0.00 WHERE total_balance IS NULL;