-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 02, 2025 at 02:28 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `mybillingapp1`
--

-- --------------------------------------------------------

--
-- Table structure for table `bills`
--

CREATE TABLE `bills` (
  `bill_id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `bill_number` varchar(50) NOT NULL,
  `customer_name` varchar(100) DEFAULT NULL,
  `customer_address` varchar(255) DEFAULT NULL,
  `customer_gstin` varchar(20) DEFAULT NULL,
  `customer_contact` varchar(20) DEFAULT NULL,
  `bill_date` datetime NOT NULL,
  `gst_type` enum('GST','Non-GST') NOT NULL,
  `total_amount` decimal(12,2) NOT NULL,
  `payment_status` enum('Paid','Unpaid','Partial') NOT NULL DEFAULT 'Paid',
  `pdf_file_path` varchar(255) DEFAULT NULL,
  `customer_id` int(11) DEFAULT NULL,
  `paid_amount` decimal(10,2) DEFAULT 0.00,
  `due_amount` decimal(10,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `bill_items`
--

CREATE TABLE `bill_items` (
  `bill_item_id` int(11) NOT NULL,
  `bill_id` int(11) NOT NULL,
  `product_id` int(11) DEFAULT NULL,
  `custom_product_name` varchar(100) DEFAULT NULL,
  `custom_gst_rate` decimal(5,2) DEFAULT NULL,
  `custom_hsn_code` varchar(20) DEFAULT NULL,
  `quantity` int(11) NOT NULL,
  `price_per_unit` decimal(10,2) NOT NULL,
  `total_price` decimal(12,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `ca_connections`
--

CREATE TABLE `ca_connections` (
  `id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `ca_id` int(11) NOT NULL,
  `status` enum('pending','approved','rejected') DEFAULT 'rejected',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `ca_employees`
--

CREATE TABLE `ca_employees` (
  `employee_id` int(11) NOT NULL,
  `ca_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `chartered_accountants`
--

CREATE TABLE `chartered_accountants` (
  `ca_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `firm_name` varchar(100) NOT NULL,
  `area` varchar(100) DEFAULT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `gst_number` varchar(20) DEFAULT NULL,
  `pan_number` varchar(20) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `city` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `pincode` varchar(20) DEFAULT NULL,
  `aadhaar_file` varchar(255) DEFAULT NULL,
  `pan_file` varchar(255) DEFAULT NULL,
  `icai_certificate_file` varchar(255) DEFAULT NULL,
  `cop_certificate_file` varchar(255) DEFAULT NULL,
  `gstin` varchar(30) DEFAULT NULL,
  `business_reg_file` varchar(255) DEFAULT NULL,
  `bank_details_file` varchar(255) DEFAULT NULL,
  `photo_file` varchar(255) DEFAULT NULL,
  `signature_file` varchar(255) DEFAULT NULL,
  `office_address_proof_file` varchar(255) DEFAULT NULL,
  `self_declaration_file` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `customers`
--

CREATE TABLE `customers` (
  `customer_id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `phone` varchar(15) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `created_date` datetime DEFAULT current_timestamp(),
  `updated_date` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `is_active` tinyint(1) DEFAULT 1,
  `total_balance` decimal(10,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `customer_ledger`
--

CREATE TABLE `customer_ledger` (
  `ledger_id` int(11) NOT NULL,
  `customer_id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `transaction_date` datetime DEFAULT current_timestamp(),
  `invoice_no` varchar(50) DEFAULT NULL,
  `particulars` varchar(255) NOT NULL,
  `debit_amount` decimal(10,2) DEFAULT 0.00,
  `credit_amount` decimal(10,2) DEFAULT 0.00,
  `balance_amount` decimal(10,2) NOT NULL,
  `transaction_type` varchar(20) NOT NULL,
  `reference_bill_id` int(11) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_date` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Triggers `customer_ledger`
--
DELIMITER $$
CREATE TRIGGER `tr_update_customer_balance` AFTER INSERT ON `customer_ledger` FOR EACH ROW BEGIN
    UPDATE customers 
    SET total_balance = NEW.balance_amount,
        updated_date = CURRENT_TIMESTAMP
    WHERE customer_id = NEW.customer_id;
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `documents`
--

CREATE TABLE `documents` (
  `document_id` int(11) NOT NULL,
  `shopkeeper_id` int(11) DEFAULT NULL,
  `ca_id` int(11) DEFAULT NULL,
  `document_name` varchar(100) NOT NULL,
  `file_path` varchar(255) NOT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `employee_clients`
--

CREATE TABLE `employee_clients` (
  `id` int(11) NOT NULL,
  `employee_id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `gst_filing_status`
--

CREATE TABLE `gst_filing_status` (
  `id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `employee_id` int(11) DEFAULT NULL,
  `month` varchar(7) NOT NULL,
  `status` enum('Filed','Not Filed') DEFAULT 'Not Filed',
  `filed_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `products`
--

CREATE TABLE `products` (
  `product_id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `product_name` varchar(100) NOT NULL,
  `barcode` varchar(50) DEFAULT NULL,
  `price` decimal(10,2) NOT NULL,
  `stock_qty` int(11) DEFAULT 0,
  `low_stock_threshold` int(11) DEFAULT 0,
  `gst_rate` decimal(5,2) DEFAULT 0.00,
  `hsn_code` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `shopkeepers`
--

CREATE TABLE `shopkeepers` (
  `shopkeeper_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `shop_name` varchar(100) NOT NULL,
  `domain` varchar(50) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `gst_number` varchar(20) DEFAULT NULL,
  `contact_number` varchar(20) DEFAULT NULL,
  `gst_doc_path` varchar(255) DEFAULT NULL,
  `pan_doc_path` varchar(255) DEFAULT NULL,
  `address_proof_path` varchar(255) DEFAULT NULL,
  `logo_path` varchar(255) DEFAULT NULL,
  `aadhaar_dl_path` varchar(255) DEFAULT NULL,
  `selfie_path` varchar(255) DEFAULT NULL,
  `gumasta_path` varchar(255) DEFAULT NULL,
  `udyam_path` varchar(255) DEFAULT NULL,
  `bank_statement_path` varchar(255) DEFAULT NULL,
  `is_verified` tinyint(1) DEFAULT 0,
  `bank_name` varchar(100) DEFAULT NULL,
  `account_number` varchar(50) DEFAULT NULL,
  `ifsc_code` varchar(20) DEFAULT NULL,
  `template_choice` varchar(20) DEFAULT 'template2',
  `city` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `pincode` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `shop_connections`
--

CREATE TABLE `shop_connections` (
  `id` int(11) NOT NULL,
  `shopkeeper_id` int(11) NOT NULL,
  `ca_id` int(11) NOT NULL,
  `status` enum('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('shopkeeper','CA','employee') NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `plain_password` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Stand-in structure for view `v_customer_summary`
-- (See below for the actual view)
--
CREATE TABLE `v_customer_summary` (
`customer_id` int(11)
,`shopkeeper_id` int(11)
,`name` varchar(100)
,`phone` varchar(15)
,`email` varchar(100)
,`address` text
,`total_balance` decimal(10,2)
,`created_date` datetime
,`total_transactions` bigint(21)
,`total_purchases` decimal(32,2)
,`total_payments` decimal(32,2)
,`last_transaction_date` datetime
,`total_bills` bigint(21)
);

-- --------------------------------------------------------

--
-- Structure for view `v_customer_summary`
--
DROP TABLE IF EXISTS `v_customer_summary`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_customer_summary`  AS SELECT `c`.`customer_id` AS `customer_id`, `c`.`shopkeeper_id` AS `shopkeeper_id`, `c`.`name` AS `name`, `c`.`phone` AS `phone`, `c`.`email` AS `email`, `c`.`address` AS `address`, `c`.`total_balance` AS `total_balance`, `c`.`created_date` AS `created_date`, count(`cl`.`ledger_id`) AS `total_transactions`, sum(case when `cl`.`debit_amount` > 0 then `cl`.`debit_amount` else 0 end) AS `total_purchases`, sum(case when `cl`.`credit_amount` > 0 then `cl`.`credit_amount` else 0 end) AS `total_payments`, max(`cl`.`transaction_date`) AS `last_transaction_date`, count(`b`.`bill_id`) AS `total_bills` FROM ((`customers` `c` left join `customer_ledger` `cl` on(`c`.`customer_id` = `cl`.`customer_id`)) left join `bills` `b` on(`c`.`customer_id` = `b`.`customer_id`)) GROUP BY `c`.`customer_id`, `c`.`shopkeeper_id`, `c`.`name`, `c`.`phone`, `c`.`email`, `c`.`address`, `c`.`total_balance`, `c`.`created_date` ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `bills`
--
ALTER TABLE `bills`
  ADD PRIMARY KEY (`bill_id`),
  ADD KEY `idx_shopkeeper_id_bills` (`shopkeeper_id`),
  ADD KEY `IX_bills_customer` (`customer_id`);

--
-- Indexes for table `bill_items`
--
ALTER TABLE `bill_items`
  ADD PRIMARY KEY (`bill_item_id`),
  ADD KEY `idx_bill_id` (`bill_id`),
  ADD KEY `idx_product_id` (`product_id`);

--
-- Indexes for table `ca_connections`
--
ALTER TABLE `ca_connections`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_connection` (`shopkeeper_id`,`ca_id`);

--
-- Indexes for table `ca_employees`
--
ALTER TABLE `ca_employees`
  ADD PRIMARY KEY (`employee_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `idx_ca_id` (`ca_id`);

--
-- Indexes for table `chartered_accountants`
--
ALTER TABLE `chartered_accountants`
  ADD PRIMARY KEY (`ca_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `customers`
--
ALTER TABLE `customers`
  ADD PRIMARY KEY (`customer_id`),
  ADD UNIQUE KEY `unique_shopkeeper_phone` (`shopkeeper_id`,`phone`),
  ADD KEY `IX_customers_shopkeeper_phone` (`shopkeeper_id`,`phone`);

--
-- Indexes for table `customer_ledger`
--
ALTER TABLE `customer_ledger`
  ADD PRIMARY KEY (`ledger_id`),
  ADD KEY `shopkeeper_id` (`shopkeeper_id`),
  ADD KEY `reference_bill_id` (`reference_bill_id`),
  ADD KEY `IX_customer_ledger_customer` (`customer_id`),
  ADD KEY `IX_customer_ledger_date` (`transaction_date`);

--
-- Indexes for table `documents`
--
ALTER TABLE `documents`
  ADD PRIMARY KEY (`document_id`),
  ADD KEY `shopkeeper_id` (`shopkeeper_id`),
  ADD KEY `ca_id` (`ca_id`);

--
-- Indexes for table `employee_clients`
--
ALTER TABLE `employee_clients`
  ADD PRIMARY KEY (`id`),
  ADD KEY `shopkeeper_id` (`shopkeeper_id`),
  ADD KEY `idx_employee_id` (`employee_id`);

--
-- Indexes for table `gst_filing_status`
--
ALTER TABLE `gst_filing_status`
  ADD PRIMARY KEY (`id`),
  ADD KEY `shopkeeper_id` (`shopkeeper_id`),
  ADD KEY `employee_id` (`employee_id`);

--
-- Indexes for table `products`
--
ALTER TABLE `products`
  ADD PRIMARY KEY (`product_id`),
  ADD KEY `idx_shopkeeper_id` (`shopkeeper_id`);

--
-- Indexes for table `shopkeepers`
--
ALTER TABLE `shopkeepers`
  ADD PRIMARY KEY (`shopkeeper_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `shop_connections`
--
ALTER TABLE `shop_connections`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_connection` (`shopkeeper_id`,`ca_id`),
  ADD KEY `ca_id` (`ca_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `bills`
--
ALTER TABLE `bills`
  MODIFY `bill_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `bill_items`
--
ALTER TABLE `bill_items`
  MODIFY `bill_item_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `ca_connections`
--
ALTER TABLE `ca_connections`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `ca_employees`
--
ALTER TABLE `ca_employees`
  MODIFY `employee_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `chartered_accountants`
--
ALTER TABLE `chartered_accountants`
  MODIFY `ca_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `customers`
--
ALTER TABLE `customers`
  MODIFY `customer_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `customer_ledger`
--
ALTER TABLE `customer_ledger`
  MODIFY `ledger_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `documents`
--
ALTER TABLE `documents`
  MODIFY `document_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `employee_clients`
--
ALTER TABLE `employee_clients`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `gst_filing_status`
--
ALTER TABLE `gst_filing_status`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `products`
--
ALTER TABLE `products`
  MODIFY `product_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `shopkeepers`
--
ALTER TABLE `shopkeepers`
  MODIFY `shopkeeper_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `shop_connections`
--
ALTER TABLE `shop_connections`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `bills`
--
ALTER TABLE `bills`
  ADD CONSTRAINT `FK_bills_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`customer_id`),
  ADD CONSTRAINT `bills_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE;

--
-- Constraints for table `bill_items`
--
ALTER TABLE `bill_items`
  ADD CONSTRAINT `bill_items_ibfk_1` FOREIGN KEY (`bill_id`) REFERENCES `bills` (`bill_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `bill_items_ibfk_2` FOREIGN KEY (`product_id`) REFERENCES `products` (`product_id`) ON DELETE CASCADE;

--
-- Constraints for table `ca_employees`
--
ALTER TABLE `ca_employees`
  ADD CONSTRAINT `ca_employees_ibfk_1` FOREIGN KEY (`ca_id`) REFERENCES `chartered_accountants` (`ca_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `ca_employees_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `chartered_accountants`
--
ALTER TABLE `chartered_accountants`
  ADD CONSTRAINT `chartered_accountants_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `customers`
--
ALTER TABLE `customers`
  ADD CONSTRAINT `customers_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `customer_ledger`
--
ALTER TABLE `customer_ledger`
  ADD CONSTRAINT `customer_ledger_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`customer_id`),
  ADD CONSTRAINT `customer_ledger_ibfk_2` FOREIGN KEY (`shopkeeper_id`) REFERENCES `users` (`user_id`),
  ADD CONSTRAINT `customer_ledger_ibfk_3` FOREIGN KEY (`reference_bill_id`) REFERENCES `bills` (`bill_id`);

--
-- Constraints for table `documents`
--
ALTER TABLE `documents`
  ADD CONSTRAINT `documents_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `documents_ibfk_2` FOREIGN KEY (`ca_id`) REFERENCES `chartered_accountants` (`ca_id`) ON DELETE CASCADE;

--
-- Constraints for table `employee_clients`
--
ALTER TABLE `employee_clients`
  ADD CONSTRAINT `employee_clients_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `ca_employees` (`employee_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `employee_clients_ibfk_2` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE;

--
-- Constraints for table `gst_filing_status`
--
ALTER TABLE `gst_filing_status`
  ADD CONSTRAINT `gst_filing_status_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`),
  ADD CONSTRAINT `gst_filing_status_ibfk_2` FOREIGN KEY (`employee_id`) REFERENCES `ca_employees` (`employee_id`);

--
-- Constraints for table `products`
--
ALTER TABLE `products`
  ADD CONSTRAINT `products_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE;

--
-- Constraints for table `shopkeepers`
--
ALTER TABLE `shopkeepers`
  ADD CONSTRAINT `shopkeepers_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `shop_connections`
--
ALTER TABLE `shop_connections`
  ADD CONSTRAINT `shop_connections_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `shop_connections_ibfk_2` FOREIGN KEY (`ca_id`) REFERENCES `chartered_accountants` (`ca_id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;

-- Add walkthrough_completed field to users table
ALTER TABLE users ADD COLUMN walkthrough_completed BOOLEAN DEFAULT FALSE;

-- Optional: Update existing users to show walkthrough (set to FALSE for all existing users)
UPDATE users SET walkthrough_completed = FALSE WHERE walkthrough_completed IS NULL;

-- Optional: Add index for better performance
CREATE INDEX idx_users_walkthrough_completed ON users(walkthrough_completed);

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

-- Purchase Bill Scanning Tables
-- Run these commands to add purchase bill scanning functionality

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


-- 1. Add discount_percent column to bill_items table
-- This will store the discount percentage applied to each line item
ALTER TABLE `bill_items` 
ADD COLUMN `discount_percent` DECIMAL(5,2) DEFAULT 0.00 
COMMENT 'Discount percentage applied to this line item';

-- 2. Add gst_mode column to bills table  
-- This will store whether the bill uses INCLUSIVE or EXCLUSIVE GST calculation
ALTER TABLE `bills` 
ADD COLUMN `gst_mode` ENUM('INCLUSIVE', 'EXCLUSIVE') DEFAULT 'EXCLUSIVE' 
COMMENT 'GST calculation mode - INCLUSIVE or EXCLUSIVE';

-- 3. Update bill_items to include discount amount storage (optional but recommended)
-- This helps with faster retrieval and audit trails
ALTER TABLE `bill_items` 
ADD COLUMN `discount_amount` DECIMAL(10,2) DEFAULT 0.00 
COMMENT 'Calculated discount amount in rupees';

-- 4. Add taxable_amount column to bill_items for better GST calculation storage
-- This stores the amount after discount but before GST
ALTER TABLE `bill_items` 
ADD COLUMN `taxable_amount` DECIMAL(12,2) DEFAULT 0.00 
COMMENT 'Taxable amount after discount, before GST';

-- 5. Add GST breakdown columns to bill_items for complete audit trail
ALTER TABLE `bill_items` 
ADD COLUMN `cgst_rate` DECIMAL(5,2) DEFAULT 0.00 
COMMENT 'CGST rate applied',
ADD COLUMN `sgst_rate` DECIMAL(5,2) DEFAULT 0.00 
COMMENT 'SGST rate applied',
ADD COLUMN `cgst_amount` DECIMAL(10,2) DEFAULT 0.00 
COMMENT 'CGST amount calculated',
ADD COLUMN `sgst_amount` DECIMAL(10,2) DEFAULT 0.00 
COMMENT 'SGST amount calculated',
ADD COLUMN `total_gst_amount` DECIMAL(10,2) DEFAULT 0.00 
COMMENT 'Total GST amount (CGST + SGST)';

-- 6. Create index for better performance on bill queries
CREATE INDEX `idx_bills_gst_mode` ON `bills` (`gst_mode`);
CREATE INDEX `idx_bills_gst_type` ON `bills` (`gst_type`);
CREATE INDEX `idx_bill_items_discount` ON `bill_items` (`discount_percent`);

-- 7. Update existing data with default values (run after adding columns)
UPDATE `bill_items` SET 
    `discount_percent` = 0.00,
    `discount_amount` = 0.00,
    `taxable_amount` = `total_price`,
    `cgst_rate` = 0.00,
    `sgst_rate` = 0.00,
    `cgst_amount` = 0.00,
    `sgst_amount` = 0.00,
    `total_gst_amount` = 0.00
WHERE `discount_percent` IS NULL;

UPDATE `bills` SET `gst_mode` = 'EXCLUSIVE' WHERE `gst_mode` IS NULL;

ALTER TABLE bills 
ADD date_with_time BOOLEAN DEFAULT FALSE;

-- Update existing bills to show date only by default
UPDATE bills SET date_with_time = FALSE WHERE date_with_time IS NULL;

-- Add gstin column to customers table
ALTER TABLE customers 
ADD COLUMN gstin VARCHAR(15) NULL 
COMMENT 'Customer GST Identification Number (15 characters max)';