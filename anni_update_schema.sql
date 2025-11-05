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