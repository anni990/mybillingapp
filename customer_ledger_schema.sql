-- Customer Ledger System Database Schema Updates (MySQL/MariaDB Compatible)
-- Execute these queries to add customer management and ledger functionality

-- 1. Create Customers table (MySQL compatible)
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    shopkeeper_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(100) NULL,
    address TEXT NULL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    total_balance DECIMAL(10,2) DEFAULT 0.00, -- Running balance (Dr positive, Cr negative)
    FOREIGN KEY (shopkeeper_id) REFERENCES users(user_id),
    UNIQUE KEY unique_shopkeeper_phone (shopkeeper_id, phone) -- Prevent duplicate phone numbers per shopkeeper
);

-- 2. Create Customer Ledger table (MySQL compatible)
CREATE TABLE customer_ledger (
    ledger_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    shopkeeper_id INT NOT NULL,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    invoice_no VARCHAR(50) NULL, -- Can be bill_id or payment reference
    particulars VARCHAR(255) NOT NULL,
    debit_amount DECIMAL(10,2) DEFAULT 0.00, -- Purchase amount
    credit_amount DECIMAL(10,2) DEFAULT 0.00, -- Payment amount
    balance_amount DECIMAL(10,2) NOT NULL, -- Running balance after this entry
    transaction_type VARCHAR(20) NOT NULL, -- 'PURCHASE', 'PAYMENT', 'ADJUSTMENT'
    reference_bill_id INT NULL, -- Link to bills table if applicable
    notes TEXT NULL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (shopkeeper_id) REFERENCES users(user_id),
    FOREIGN KEY (reference_bill_id) REFERENCES bills(bill_id)
);

-- 3. Update Bills table to include customer reference
ALTER TABLE bills ADD COLUMN customer_id INT NULL;
ALTER TABLE bills ADD COLUMN payment_status VARCHAR(20) DEFAULT 'PAID'; -- 'PAID', 'PARTIAL', 'UNPAID'
ALTER TABLE bills ADD COLUMN paid_amount DECIMAL(10,2) DEFAULT 0.00;
ALTER TABLE bills ADD COLUMN due_amount DECIMAL(10,2) DEFAULT 0.00;

-- Add foreign key constraint
ALTER TABLE bills ADD CONSTRAINT FK_bills_customer 
FOREIGN KEY (customer_id) REFERENCES customers(customer_id);

-- 4. Create indexes for better performance
CREATE INDEX IX_customers_shopkeeper_phone ON customers(shopkeeper_id, phone);
CREATE INDEX IX_customer_ledger_customer ON customer_ledger(customer_id);
CREATE INDEX IX_customer_ledger_date ON customer_ledger(transaction_date);
CREATE INDEX IX_bills_customer ON bills(customer_id);

-- 5. Create trigger to update customer balance when ledger entry is added (MySQL compatible)
DELIMITER //
CREATE TRIGGER tr_update_customer_balance
AFTER INSERT ON customer_ledger
FOR EACH ROW
BEGIN
    UPDATE customers 
    SET total_balance = NEW.balance_amount,
        updated_date = CURRENT_TIMESTAMP
    WHERE customer_id = NEW.customer_id;
END//
DELIMITER ;

-- 6. Sample data views for reporting (MySQL compatible)
CREATE VIEW v_customer_summary AS
SELECT 
    c.customer_id,
    c.shopkeeper_id,
    c.name,
    c.phone,
    c.email,
    c.address,
    c.total_balance,
    c.created_date,
    COUNT(cl.ledger_id) as total_transactions,
    SUM(CASE WHEN cl.debit_amount > 0 THEN cl.debit_amount ELSE 0 END) as total_purchases,
    SUM(CASE WHEN cl.credit_amount > 0 THEN cl.credit_amount ELSE 0 END) as total_payments,
    MAX(cl.transaction_date) as last_transaction_date,
    COUNT(b.bill_id) as total_bills
FROM customers c
LEFT JOIN customer_ledger cl ON c.customer_id = cl.customer_id
LEFT JOIN bills b ON c.customer_id = b.customer_id
GROUP BY c.customer_id, c.shopkeeper_id, c.name, c.phone, c.email, c.address, c.total_balance, c.created_date;

-- 7. Stored procedure to add ledger entry and update balance (MySQL compatible)
DELIMITER //
CREATE PROCEDURE sp_add_ledger_entry(
    IN p_customer_id INT,
    IN p_shopkeeper_id INT,
    IN p_invoice_no VARCHAR(50),
    IN p_particulars VARCHAR(255),
    IN p_debit_amount DECIMAL(10,2),
    IN p_credit_amount DECIMAL(10,2),
    IN p_transaction_type VARCHAR(20),
    IN p_reference_bill_id INT,
    IN p_notes TEXT
)
BEGIN
    DECLARE v_current_balance DECIMAL(10,2) DEFAULT 0.00;
    DECLARE v_new_balance DECIMAL(10,2);
    
    -- Get current balance
    SELECT IFNULL(total_balance, 0) INTO v_current_balance 
    FROM customers WHERE customer_id = p_customer_id;
    
    -- Calculate new balance (Debit increases, Credit decreases)
    SET v_new_balance = v_current_balance + p_debit_amount - p_credit_amount;
    
    -- Insert ledger entry
    INSERT INTO customer_ledger (
        customer_id, shopkeeper_id, invoice_no, particulars, 
        debit_amount, credit_amount, balance_amount, 
        transaction_type, reference_bill_id, notes
    )
    VALUES (
        p_customer_id, p_shopkeeper_id, p_invoice_no, p_particulars,
        p_debit_amount, p_credit_amount, v_new_balance,
        p_transaction_type, p_reference_bill_id, p_notes
    );
    
    -- Update customer balance
    UPDATE customers 
    SET total_balance = v_new_balance, updated_date = CURRENT_TIMESTAMP
    WHERE customer_id = p_customer_id;
    
    SELECT v_new_balance as new_balance;
END//
DELIMITER ;

-- 8. Function to get customer statement (MySQL compatible - using procedure instead)
DELIMITER //
CREATE PROCEDURE sp_get_customer_statement(
    IN p_customer_id INT,
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    SELECT 
        ledger_id,
        transaction_date,
        invoice_no,
        particulars,
        debit_amount,
        credit_amount,
        balance_amount,
        transaction_type,
        notes
    FROM customer_ledger
    WHERE customer_id = p_customer_id
    AND (p_start_date IS NULL OR DATE(transaction_date) >= p_start_date)
    AND (p_end_date IS NULL OR DATE(transaction_date) <= p_end_date)
    ORDER BY transaction_date ASC, ledger_id ASC;
END//
DELIMITER ;