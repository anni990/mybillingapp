-- SQL queries to add purchase bill scanning tables to the database

-- Create purchase_bills table
CREATE TABLE `purchase_bills` (
  `purchase_bill_id` int(11) NOT NULL AUTO_INCREMENT,
  `shopkeeper_id` int(11) NOT NULL,
  `vendor_name` varchar(200) DEFAULT NULL,
  `vendor_address` text DEFAULT NULL,
  `vendor_gst_number` varchar(20) DEFAULT NULL,
  `vendor_phone` varchar(20) DEFAULT NULL,
  `vendor_email` varchar(100) DEFAULT NULL,
  `invoice_number` varchar(100) DEFAULT NULL,
  `bill_date` date DEFAULT NULL,
  `total_amount` decimal(12,2) DEFAULT NULL,
  `tax_amount` decimal(10,2) DEFAULT NULL,
  `discount_amount` decimal(10,2) DEFAULT NULL,
  `scanned_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `file_path` varchar(255) DEFAULT NULL,
  `raw_llm_response` text DEFAULT NULL,
  `processing_status` enum('processing','completed','failed') DEFAULT 'processing',
  `error_message` text DEFAULT NULL,
  PRIMARY KEY (`purchase_bill_id`),
  KEY `idx_shopkeeper_id` (`shopkeeper_id`),
  KEY `idx_processing_status` (`processing_status`),
  KEY `idx_scanned_at` (`scanned_at`),
  CONSTRAINT `fk_purchase_bills_shopkeeper` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create purchase_bill_items table
CREATE TABLE `purchase_bill_items` (
  `item_id` int(11) NOT NULL AUTO_INCREMENT,
  `purchase_bill_id` int(11) NOT NULL,
  `item_name` varchar(200) NOT NULL,
  `quantity` decimal(10,3) DEFAULT NULL,
  `unit_price` decimal(10,2) DEFAULT NULL,
  `total_price` decimal(12,2) DEFAULT NULL,
  `gst_rate` decimal(5,2) DEFAULT NULL,
  `hsn_code` varchar(20) DEFAULT NULL,
  `matched_product_id` int(11) DEFAULT NULL,
  `is_new_product` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`item_id`),
  KEY `idx_purchase_bill_id` (`purchase_bill_id`),
  KEY `idx_matched_product_id` (`matched_product_id`),
  KEY `idx_is_new_product` (`is_new_product`),
  CONSTRAINT `fk_purchase_bill_items_bill` FOREIGN KEY (`purchase_bill_id`) REFERENCES `purchase_bills` (`purchase_bill_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_purchase_bill_items_product` FOREIGN KEY (`matched_product_id`) REFERENCES `products` (`product_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create directory for storing purchase bill files
-- This needs to be done at OS level:
-- mkdir -p app/static/purchase_bills