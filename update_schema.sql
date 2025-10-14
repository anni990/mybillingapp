-- Update Schema: Add Invoice Numbering Feature
-- Run these commands manually in your MySQL database

-- Add invoice numbering columns to shopkeepers table
ALTER TABLE shopkeepers 
ADD COLUMN invoice_prefix VARCHAR(20) DEFAULT '',
ADD COLUMN invoice_starting_number INT DEFAULT 1,
ADD COLUMN current_invoice_number INT DEFAULT 1;

-- Set default values for existing shopkeepers (empty prefix = timestamp-based numbering)
UPDATE shopkeepers 
SET invoice_prefix = '', 
    invoice_starting_number = 1, 
    current_invoice_number = 1 
WHERE invoice_prefix IS NULL;