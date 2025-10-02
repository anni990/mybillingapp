-- ALTER TABLE shopkeepers ADD COLUMN gst_doc_path VARCHAR(255);

-- ALTER TABLE shopkeepers ADD COLUMN pan_doc_path VARCHAR(255);

-- ALTER TABLE shopkeepers ADD COLUMN address_proof_path VARCHAR(255);

-- ALTER TABLE users ADD COLUMN plain_password VARCHAR(255);

-- ALTER TABLE ca_connections
-- MODIFY status ENUM(
--     'pending',
--     'approved',
--     'rejected'
-- ) NOT NULL DEFAULT 'pending',
-- ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
-- ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- CREATE TABLE shop_connections (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     shopkeeper_id INT NOT NULL,
--     ca_id INT NOT NULL,
--     status ENUM(
--         'pending',
--         'approved',
--         'rejected'
--     ) NOT NULL DEFAULT 'pending',
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers (shopkeeper_id) ON DELETE CASCADE,
--     FOREIGN KEY (ca_id) REFERENCES chartered_accountants (ca_id) ON DELETE CASCADE,
--     UNIQUE KEY unique_connection (shopkeeper_id, ca_id)
-- );

-- ALTER TABLE chartered_accountants
--   ADD COLUMN aadhaar_file VARCHAR(255),
--   ADD COLUMN pan_file VARCHAR(255),
--   ADD COLUMN icai_certificate_file VARCHAR(255),
--   ADD COLUMN cop_certificate_file VARCHAR(255),
--   ADD COLUMN gstin VARCHAR(30),
--   ADD COLUMN business_reg_file VARCHAR(255),
--   ADD COLUMN bank_details_file VARCHAR(255),
--   ADD COLUMN photo_file VARCHAR(255),
--   ADD COLUMN signature_file VARCHAR(255),
--   ADD COLUMN office_address_proof_file VARCHAR(255),
--   ADD COLUMN self_declaration_file VARCHAR(255);

--   CREATE TABLE gst_filing_status (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     shopkeeper_id INT NOT NULL,
--     employee_id INT,
--     month VARCHAR(7) NOT NULL, -- Format: YYYY-MM
--     status ENUM('Filed', 'Not Filed') DEFAULT 'Not Filed',
--     filed_at DATETIME,
--     FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id),
--     FOREIGN KEY (employee_id) REFERENCES ca_employees(employee_id)
--   );
-- ALTER TABLE employee_clients ADD CONSTRAINT unique_employee_client UNIQUE (employee_id, shopkeeper_id);

-- Migration to support custom products in BillItem table (SQL Server syntax)
-- This adds fields to store custom product information when product_id is null

-- Step 1: Make product_id nullable (if it's currently NOT NULL)
ALTER TABLE bill_items ALTER COLUMN product_id INT NULL;

-- Step 2: Add new columns for custom products
ALTER TABLE bill_items ADD custom_product_name NVARCHAR(100) NULL;
ALTER TABLE bill_items ADD custom_gst_rate DECIMAL(5,2) NULL;
ALTER TABLE bill_items ADD custom_hsn_code NVARCHAR(20) NULL;

-- Step 3: Add a check constraint to ensure either product_id or custom_product_name is provided
ALTER TABLE bill_items ADD CONSTRAINT chk_product_or_custom 
CHECK (
    (product_id IS NOT NULL AND custom_product_name IS NULL) OR 
    (product_id IS NULL AND custom_product_name IS NOT NULL)
);
