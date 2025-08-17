-- ERP Software for Retail Shopkeepers and CAs
-- Complete MySQL Schema

-- 1. User Accounts
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('shopkeeper', 'CA', 'employee') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    plain_password VARCHAR(255),
);

-- 2. Shopkeeper Profile
CREATE TABLE shopkeepers (
    shopkeeper_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    shop_name VARCHAR(100) NOT NULL,
    domain VARCHAR(50),
    address VARCHAR(255),
    gst_number VARCHAR(20),
    contact_number VARCHAR(20),
    gst_doc_path VARCHAR(255),
    pan_doc_path VARCHAR(255),
    address_proof_path VARCHAR(255),
    logo_path VARCHAR(255),
    aadhaar_dl_path VARCHAR(255),
    selfie_path VARCHAR(255),
    gumasta_path VARCHAR(255),
    udyam_path VARCHAR(255),
    bank_statement_path VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    bank_name VARCHAR(100),
    account_number VARCHAR(50),
    ifsc_code VARCHAR(20),
    template_choice VARCHAR(20) DEFAULT 'template2',
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. Chartered Accountant Profile
CREATE TABLE chartered_accountants (
    ca_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    firm_name VARCHAR(100) NOT NULL,
    area VARCHAR(100),
    contact_number VARCHAR(20),
    gst_number VARCHAR(20),
    pan_number VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(20),
    aadhaar_file VARCHAR(255),
    pan_file VARCHAR(255),
    icai_certificate_file VARCHAR(255),
    cop_certificate_file VARCHAR(255),
    gstin VARCHAR(30),
    business_reg_file VARCHAR(255),
    bank_details_file VARCHAR(255),
    photo_file VARCHAR(255),
    signature_file VARCHAR(255),
    office_address_proof_file VARCHAR(255),
    self_declaration_file VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. CA Employees
CREATE TABLE ca_employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    ca_id INT NOT NULL,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE employee_clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    shopkeeper_id INT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES ca_employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE
);

-- 5. Products & Stock
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    barcode VARCHAR(50),
    price DECIMAL(10,2) NOT NULL,
    stock_qty INT DEFAULT 0,
    low_stock_threshold INT DEFAULT 0,
    gst_rate DECIMAL(5,2) DEFAULT 0,
    hsn_code VARCHAR(20),
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE
);

-- 6. Bills
CREATE TABLE bills (
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    bill_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100),
    customer_address VARCHAR(255) NULL,
    customer_gstin VARCHAR(20) NULL,
    customer_contact VARCHAR(20),
    bill_date DATE NOT NULL,
    gst_type ENUM('GST', 'Non-GST') NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    payment_status ENUM('Paid', 'Unpaid', 'Partial') NOT NULL,
    pdf_file_path VARCHAR(255),
    amount_paid NUMERIC(12,2) DEFAULT 0 NULL,
    amount_unpaid NUMERIC(12,2) DEFAULT 0 NULL,
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE
);

CREATE TABLE bill_items (
    bill_item_id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    price_per_unit DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- 7. Shopkeeper-CA Connection
CREATE TABLE ca_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    ca_id INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'rejected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_connection (shopkeeper_id, ca_id)
);

-- 8. Documents
CREATE TABLE documents (
    document_id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT,
    ca_id INT,
    document_name VARCHAR(100) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE,
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE CASCADE
);

-- Add indexes for performance (optional)
CREATE INDEX idx_shopkeeper_id ON products(shopkeeper_id);
CREATE INDEX idx_bill_id ON bill_items(bill_id);
CREATE INDEX idx_product_id ON bill_items(product_id);
CREATE INDEX idx_ca_id ON ca_employees(ca_id);
CREATE INDEX idx_employee_id ON employee_clients(employee_id);
CREATE INDEX idx_shopkeeper_id_bills ON bills(shopkeeper_id); 

CREATE TABLE shop_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    ca_id INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE,
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE CASCADE,
    UNIQUE KEY unique_connection (shopkeeper_id, ca_id)
); 

CREATE TABLE gst_filing_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    employee_id INT,
    month VARCHAR(7) NOT NULL, -- Format: YYYY-MM
    status ENUM('Filed', 'Not Filed') DEFAULT 'Not Filed',
    filed_at DATETIME,
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id),
    FOREIGN KEY (employee_id) REFERENCES ca_employees(employee_id)
);