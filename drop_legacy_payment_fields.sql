-- Migration to remove duplicate payment fields from bills table
-- This script removes the legacy amount_paid and amount_unpaid columns
-- and keeps only the newer paid_amount and due_amount fields

-- First, ensure all data is migrated to the new fields (if not already done)
UPDATE bills SET
    paid_amount = COALESCE(amount_paid, 0),
    due_amount = COALESCE(amount_unpaid, 0)
WHERE paid_amount = 0 AND due_amount = 0;

-- Drop the legacy columns
ALTER TABLE bills DROP COLUMN amount_paid;
ALTER TABLE bills DROP COLUMN amount_unpaid;