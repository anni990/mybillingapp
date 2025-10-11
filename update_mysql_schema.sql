-- MySQL Schema Update Commands
-- File: update_mysql_schema.sql
-- Purpose: Update existing MySQL/MariaDB database with missing fields
-- Date: October 11, 2025
-- 
-- Run these commands on your existing MySQL/MariaDB database to add missing fields

-- Connect to your MySQL database and run these commands:
USE mybillingapp1;  -- Replace with your database name

-- 1. Add missing walkthrough_completed field to users table
ALTER TABLE `users` 
ADD COLUMN `walkthrough_completed` TINYINT(1) NOT NULL DEFAULT 0 
AFTER `plain_password`;

-- 2. Add missing about_me field to chartered_accountants table
ALTER TABLE `chartered_accountants` 
ADD COLUMN `about_me` VARCHAR(2000) NULL 
AFTER `self_declaration_file`;

-- 3. Verify the updates were applied successfully
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE (TABLE_NAME = 'users' AND COLUMN_NAME = 'walkthrough_completed')
   OR (TABLE_NAME = 'chartered_accountants' AND COLUMN_NAME = 'about_me')
   AND TABLE_SCHEMA = DATABASE()
ORDER BY TABLE_NAME, COLUMN_NAME;

-- 4. Check table structure to confirm changes
DESCRIBE `users`;
DESCRIBE `chartered_accountants`;

-- Optional: Update existing records if needed
-- Uncomment and modify these queries as needed:

-- Set walkthrough_completed to 1 for existing users who should skip the walkthrough
-- UPDATE `users` SET `walkthrough_completed` = 1 WHERE `role` = 'CA' OR `role` = 'employee';

-- Add default about_me text for existing CAs who don't have this field
-- UPDATE `chartered_accountants` 
-- SET `about_me` = 'Professional chartered accountant providing comprehensive financial services.' 
-- WHERE `about_me` IS NULL;

SELECT 'MySQL schema update completed successfully!' AS status;