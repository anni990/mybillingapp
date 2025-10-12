-- ================================================
-- MyBillingApp Database Update Schema
-- ================================================
-- This file contains incremental database updates
-- Run these commands in order based on your current schema version

-- ================================================
-- Update 2025-10-12: CA Connection Request Fix
-- ================================================
-- Description: Fixed CA connection request functionality
-- Issue: Code was using incorrect field name 'request_date' instead of 'created_at'
-- Solution: No database changes needed - schema was already correct

-- Verify shop_connections table structure (should already be correct)
-- If your table doesn't match this structure, run the CREATE statement below

/*
Expected shop_connections table structure:
CREATE TABLE `shop_connections` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `shopkeeper_id` int(11) NOT NULL,
  `ca_id` int(11) NOT NULL,
  `status` enum('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `shopkeeper_id` (`shopkeeper_id`),
  KEY `ca_id` (`ca_id`),
  CONSTRAINT `shop_connections_ibfk_1` FOREIGN KEY (`shopkeeper_id`) REFERENCES `shopkeepers` (`shopkeeper_id`) ON DELETE CASCADE,
  CONSTRAINT `shop_connections_ibfk_2` FOREIGN KEY (`ca_id`) REFERENCES `chartered_accountants` (`ca_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
*/

-- No SQL updates required for this fix
-- Changes were made in application code only:
-- 1. Fixed JavaScript route from '/shopkeeper/send_connection_request' to '/shopkeeper/request_connection/{ca_id}'
-- 2. Fixed Python code to use existing 'created_at' field instead of non-existent 'request_date'
-- 3. Added AJAX support to route with proper JSON responses

-- ================================================
-- Future Updates
-- ================================================
-- Add new database schema updates below this line
-- Format: Update YYYY-MM-DD: Description
