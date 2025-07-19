ALTER TABLE shopkeepers ADD COLUMN gst_doc_path VARCHAR(255);

ALTER TABLE shopkeepers ADD COLUMN pan_doc_path VARCHAR(255);

ALTER TABLE shopkeepers ADD COLUMN address_proof_path VARCHAR(255);

ALTER TABLE users ADD COLUMN plain_password VARCHAR(255);

ALTER TABLE ca_connections
MODIFY status ENUM(
    'pending',
    'approved',
    'rejected'
) NOT NULL DEFAULT 'pending',
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

CREATE TABLE shop_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    ca_id INT NOT NULL,
    status ENUM(
        'pending',
        'approved',
        'rejected'
    ) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (shopkeeper_id) REFERENCES shopkeepers (shopkeeper_id) ON DELETE CASCADE,
    FOREIGN KEY (ca_id) REFERENCES chartered_accountants (ca_id) ON DELETE CASCADE,
    UNIQUE KEY unique_connection (shopkeeper_id, ca_id)
);

ALTER TABLE bills
ADD COLUMN amount_paid NUMERIC(12,2) DEFAULT 0 NULL,
ADD COLUMN amount_unpaid NUMERIC(12,2) DEFAULT 0 NULL;

ALTER TABLE products ADD COLUMN gst_rate DECIMAL(5,2) DEFAULT 0;