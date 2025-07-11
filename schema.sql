-- ERP Software for Retail Shopkeepers and CAs
-- Complete MySQL Schema

-- 1. User Accounts
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('shopkeeper', 'CA', 'employee') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Shopkeeper Profile
CREATE TABLE shopkeepers (
    shopkeeper_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    shop_name VARCHAR(100) NOT NULL,
    domain VARCHAR(50), -- e.g., grocery, medical, etc.
    address VARCHAR(255),
    gst_number VARCHAR(20),
    contact_number VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Add document path columns to shopkeepers table
ALTER TABLE shopkeepers ADD COLUMN gst_doc_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN pan_doc_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN address_proof_path VARCHAR(255);

-- 3. Chartered Accountant Profile
CREATE TABLE chartered_accountants (
    ca_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    firm_name VARCHAR(100) NOT NULL,
    area VARCHAR(100),
    boost_status BOOLEAN DEFAULT FALSE,
    contact_number VARCHAR(20),
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
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE
);

-- 6. Bills
CREATE TABLE bills (
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    bill_number VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100),
    customer_contact VARCHAR(20),
    bill_date DATE NOT NULL,
    gst_type ENUM('GST', 'Non-GST') NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    payment_status ENUM('Paid', 'Unpaid', 'Partial') NOT NULL,
    pdf_file_path VARCHAR(255),
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
    status ENUM('pending', 'approved') NOT NULL DEFAULT 'pending',
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers(shopkeeper_id) ON DELETE CASCADE,
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants(ca_id) ON DELETE CASCADE
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