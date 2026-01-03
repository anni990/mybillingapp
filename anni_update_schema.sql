-- -- SQL queries to add purchase bill scanning tables to the database

-- -- Create purchase_bills table
-- CREATE TABLE `purchase_bills` (
--   `purchase_bill_id` int(11) NOT NULL AUTO_INCREMENT,
--   `shopkeeper_id` int(11) NOT NULL,
--   `vendor_name` varchar(200) DEFAULT NULL,
--   `vendor_address` text DEFAULT NULL,
--   `vendor_gst_number` varchar(20) DEFAULT NULL,
--   `vendor_phone` varchar(20) DEFAULT NULL,
--   `vendor_email` varchar(100) DEFAULT NULL,
--   `invoice_number` varchar(100) DEFAULT NULL,
--   `bill_date` date DEFAULT NULL,
--   `total_amount` decimal(12,2) DEFAULT NULL,
--   `tax_amount` decimal(10,2) DEFAULT NULL,
--   `discount_amount` decimal(10,2) DEFAULT NULL,
--   `scanned_at` datetime DEFAULT CURRENT_TIMESTAMP,
--   `file_path` varchar(255) DEFAULT NULL,
--   `raw_llm_response` text DEFAULT NULL,
--   `processing_status` enum('processing','completed','failed') DEFAULT 'processing',
--   `error_message` text DEFAULT NULL,
--   PRIMARY KEY (`purchase_bill_id`),
--   KEY `idx_shopkeeper_id` (`shopkeeper_id`),
--   KEY `idx_processing_status` (`processing_status`),
--   KEY `idx_scanned_at` (`scanned_at`),
--   CONSTRAINT `fk_purchase_bills_shopkeeper` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -- Create purchase_bill_items table
-- CREATE TABLE `purchase_bill_items` (
--   `item_id` int(11) NOT NULL AUTO_INCREMENT,
--   `purchase_bill_id` int(11) NOT NULL,
--   `item_name` varchar(200) NOT NULL,
--   `quantity` decimal(10,3) DEFAULT NULL,
--   `unit_price` decimal(10,2) DEFAULT NULL,
--   `total_price` decimal(12,2) DEFAULT NULL,
--   `gst_rate` decimal(5,2) DEFAULT NULL,
--   `hsn_code` varchar(20) DEFAULT NULL,
--   `matched_product_id` int(11) DEFAULT NULL,
--   `is_new_product` tinyint(1) DEFAULT 1,
--   PRIMARY KEY (`item_id`),
--   KEY `idx_purchase_bill_id` (`purchase_bill_id`),
--   KEY `idx_matched_product_id` (`matched_product_id`),
--   KEY `idx_is_new_product` (`is_new_product`),
--   CONSTRAINT `fk_purchase_bill_items_bill` FOREIGN KEY (`purchase_bill_id`) REFERENCES `purchase_bills` (`purchase_bill_id`) ON DELETE CASCADE,
--   CONSTRAINT `fk_purchase_bill_items_product` FOREIGN KEY (`matched_product_id`) REFERENCES `products` (`product_id`) ON DELETE SET NULL
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -- Create directory for storing purchase bill files
-- -- This needs to be done at OS level:
-- -- mkdir -p app/static/purchase_bills


-- -- 1. Add discount_percent column to bill_items table
-- -- This will store the discount percentage applied to each line item
-- ALTER TABLE `bill_items` 
-- ADD COLUMN `discount_percent` DECIMAL(5,2) DEFAULT 0.00 
-- COMMENT 'Discount percentage applied to this line item';

-- -- 2. Add gst_mode column to bills table  
-- -- This will store whether the bill uses INCLUSIVE or EXCLUSIVE GST calculation
-- ALTER TABLE `bills` 
-- ADD COLUMN `gst_mode` ENUM('INCLUSIVE', 'EXCLUSIVE') DEFAULT 'EXCLUSIVE' 
-- COMMENT 'GST calculation mode - INCLUSIVE or EXCLUSIVE';

-- -- 3. Update bill_items to include discount amount storage (optional but recommended)
-- -- This helps with faster retrieval and audit trails
-- ALTER TABLE `bill_items` 
-- ADD COLUMN `discount_amount` DECIMAL(10,2) DEFAULT 0.00 
-- COMMENT 'Calculated discount amount in rupees';

-- -- 4. Add taxable_amount column to bill_items for better GST calculation storage
-- -- This stores the amount after discount but before GST
-- ALTER TABLE `bill_items` 
-- ADD COLUMN `taxable_amount` DECIMAL(12,2) DEFAULT 0.00 
-- COMMENT 'Taxable amount after discount, before GST';

-- -- 5. Add GST breakdown columns to bill_items for complete audit trail
-- ALTER TABLE `bill_items` 
-- ADD COLUMN `cgst_rate` DECIMAL(5,2) DEFAULT 0.00 
-- COMMENT 'CGST rate applied',
-- ADD COLUMN `sgst_rate` DECIMAL(5,2) DEFAULT 0.00 
-- COMMENT 'SGST rate applied',
-- ADD COLUMN `cgst_amount` DECIMAL(10,2) DEFAULT 0.00 
-- COMMENT 'CGST amount calculated',
-- ADD COLUMN `sgst_amount` DECIMAL(10,2) DEFAULT 0.00 
-- COMMENT 'SGST amount calculated',
-- ADD COLUMN `total_gst_amount` DECIMAL(10,2) DEFAULT 0.00 
-- COMMENT 'Total GST amount (CGST + SGST)';

-- -- 6. Create index for better performance on bill queries
-- CREATE INDEX `idx_bills_gst_mode` ON `bills` (`gst_mode`);
-- CREATE INDEX `idx_bills_gst_type` ON `bills` (`gst_type`);
-- CREATE INDEX `idx_bill_items_discount` ON `bill_items` (`discount_percent`);

-- -- 7. Update existing data with default values (run after adding columns)
-- UPDATE `bill_items` SET 
--     `discount_percent` = 0.00,
--     `discount_amount` = 0.00,
--     `taxable_amount` = `total_price`,
--     `cgst_rate` = 0.00,
--     `sgst_rate` = 0.00,
--     `cgst_amount` = 0.00,
--     `sgst_amount` = 0.00,
--     `total_gst_amount` = 0.00
-- WHERE `discount_percent` IS NULL;

-- UPDATE `bills` SET `gst_mode` = 'EXCLUSIVE' WHERE `gst_mode` IS NULL;

-- ALTER TABLE bills 
-- ADD date_with_time BOOLEAN DEFAULT FALSE;

-- -- Update existing bills to show date only by default
-- UPDATE bills SET date_with_time = FALSE WHERE date_with_time IS NULL;

-- -- Add gstin column to customers table
-- ALTER TABLE customers 
-- ADD COLUMN gstin VARCHAR(15) NULL 
-- COMMENT 'Customer GST Identification Number (15 characters max)';

-- Subscription System Migration Script
-- Adds subscription_plan, daily_gst_bill_count, and last_bill_date to shopkeepers table
-- Run this script to update existing database schema

-- -- Step 1: Create ENUM type for plan_types (MySQL uses ENUM syntax)
-- ALTER TABLE shopkeepers 
-- ADD COLUMN subscription_plan ENUM('free', 'lite', 'gold') NOT NULL DEFAULT 'free' AFTER current_invoice_number;

-- -- Step 2: Add daily billing counter field
-- ALTER TABLE shopkeepers 
-- ADD COLUMN daily_gst_bill_count INT NOT NULL DEFAULT 0 AFTER subscription_plan;

-- -- Step 3: Add last bill date field
-- ALTER TABLE shopkeepers 
-- ADD COLUMN last_bill_date DATE DEFAULT NULL AFTER daily_gst_bill_count;

-- -- Step 4: Update all existing shopkeepers to 'free' plan (default already set above)
-- UPDATE shopkeepers SET subscription_plan = 'free' WHERE subscription_plan IS NULL;

-- -- Step 5: Reset all daily counters to 0 (default already set above)  
-- UPDATE shopkeepers SET daily_gst_bill_count = 0 WHERE daily_gst_bill_count IS NULL;

-- -- Verify the changes
-- SELECT COUNT(*) as total_shopkeepers, 
--        COUNT(CASE WHEN subscription_plan = 'free' THEN 1 END) as free_plan_count,
--        COUNT(CASE WHEN subscription_plan = 'lite' THEN 1 END) as lite_plan_count,
--        COUNT(CASE WHEN subscription_plan = 'gold' THEN 1 END) as gold_plan_count
-- FROM shopkeepers;

-- -- Show sample data to verify migration
-- SELECT shopkeeper_id, shop_name, subscription_plan, daily_gst_bill_count, last_bill_date 
-- FROM shopkeepers 
-- LIMIT 5;

-- -- SQL commands to update database for Google OAuth integration
-- -- Run these commands in your MySQL database

-- -- 1. Make password_hash nullable for OAuth users
-- ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NULL;

-- -- 2. Add Google OAuth columns
-- ALTER TABLE users ADD COLUMN google_id VARCHAR(256) UNIQUE NULL COMMENT 'Google OAuth user ID';
-- ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50) NULL COMMENT 'OAuth provider (google, etc.)';
-- ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512) NULL COMMENT 'User avatar/profile picture URL';

-- -- 3. Add index for faster OAuth lookups
-- CREATE INDEX idx_users_google_id ON users(google_id);
-- CREATE INDEX idx_users_oauth_provider ON users(oauth_provider);

-- -- 4. Verify the changes
-- DESCRIBE users;

-- -- 5. Optional: Check if columns were added successfully
-- SELECT 
--     COLUMN_NAME, 
--     DATA_TYPE, 
--     IS_NULLABLE, 
--     COLUMN_DEFAULT,
--     COLUMN_COMMENT
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_NAME = 'users' 
-- AND TABLE_SCHEMA = DATABASE()
-- ORDER BY ORDINAL_POSITION;

-- -- Notes:
-- -- - Run these commands one by one in your MySQL client
-- -- - If any column already exists, you'll get a "Duplicate column name" error (which is safe to ignore)
-- -- - Make sure to backup your database before running these commands
-- -- - Replace 'your_database_name' with your actual database name if needed

-- -- SQL commands to update database for Watermark Logic Implementation
-- -- Run these commands in your MySQL database

-- -- 1. Add watermark settings to shopkeepers table
-- ALTER TABLE shopkeepers ADD COLUMN watermark_enabled BOOLEAN DEFAULT TRUE COMMENT 'Whether watermark is enabled on bills';
-- ALTER TABLE shopkeepers ADD COLUMN watermark_type VARCHAR(20) DEFAULT 'diagonal' COMMENT 'Type of watermark: diagonal, bottom, centered';

-- -- 2. Set watermark defaults based on subscription plan
-- UPDATE shopkeepers SET 
--     watermark_enabled = CASE 
--         WHEN subscription_plan = 'free' THEN TRUE 
--         ELSE FALSE 
--     END,
--     watermark_type = 'diagonal'
-- WHERE watermark_enabled IS NULL OR watermark_type IS NULL;

-- -- 3. Verify the changes
-- DESCRIBE shopkeepers;

-- -- 4. Check the updated shopkeeper records
-- SELECT shop_name, subscription_plan, watermark_enabled, watermark_type FROM shopkeepers LIMIT 10;

-- -- Notes:
-- -- - Free users: watermark_enabled = TRUE (mandatory, cannot be changed)
-- -- - Lite/Gold users: watermark_enabled = FALSE (can be toggled from profile)
-- -- - All users can select watermark_type: 'diagonal', 'bottom', or 'centered'