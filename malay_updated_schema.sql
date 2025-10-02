---------------------------------------Malay changes---------------------------------------


ALTER TABLE bills
ADD COLUMN amount_paid NUMERIC(12,2) DEFAULT 0 NULL,
ADD COLUMN amount_unpaid NUMERIC(12,2) DEFAULT 0 NULL;


ALTER TABLE products ADD COLUMN gst_rate DECIMAL(5,2) DEFAULT 0;
ALTER TABLE products ADD COLUMN hsn_code VARCHAR(20);

-- Add required document columns for shopkeepers
ALTER TABLE shopkeepers ADD COLUMN aadhaar_dl_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN selfie_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN gumasta_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN udyam_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN bank_statement_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
-- GST Certificate is also required for verification
ALTER TABLE shopkeepers ADD COLUMN bank_name VARCHAR(100);
ALTER TABLE shopkeepers ADD COLUMN account_number VARCHAR(50);
ALTER TABLE shopkeepers ADD COLUMN ifsc_code VARCHAR(20);

-- Add template_choice column for shopkeepers with default template2
ALTER TABLE shopkeepers ADD COLUMN template_choice VARCHAR(20) DEFAULT 'template2';