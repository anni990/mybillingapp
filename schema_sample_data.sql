-- Sample data for users
INSERT INTO users (user_id, username, email, password_hash, role, created_at) VALUES
(1, 'shopgrocery', 'shopgrocery@example.com', '$2b$12$abcdefghijklmnopqrstuv', 'shopkeeper', NOW()),
(2, 'caamit', 'caamit@example.com', '$2b$12$abcdefghijklmnopqrstuv', 'CA', NOW()),
(3, 'shopmedical', 'shopmedical@example.com', '$2b$12$abcdefghijklmnopqrstuv', 'shopkeeper', NOW());

-- Sample data for shopkeepers
INSERT INTO shopkeepers (shopkeeper_id, user_id, shop_name, domain, address, gst_number, contact_number) VALUES
(1, 1, 'Grocery Mart', 'grocery', '123 Main St', 'GSTIN1234', '9876543210'),
(2, 3, 'Medical Store', 'medical', '456 Health Ave', 'GSTIN5678', '9123456780');

-- Example update for new columns
UPDATE shopkeepers SET gst_doc_path=NULL, pan_doc_path=NULL, address_proof_path=NULL;

-- Sample data for chartered accountants
INSERT INTO chartered_accountants (ca_id, user_id, firm_name, area, boost_status, contact_number) VALUES
(1, 2, 'Amit & Co', 'Downtown', 1, '9988776655');

-- Sample data for CA connections
INSERT INTO ca_connections (id, shopkeeper_id, ca_id, status) VALUES
(1, 1, 1, 'approved'),
(2, 2, 1, 'pending');

-- Sample data for products
INSERT INTO products (product_id, shopkeeper_id, product_name, barcode, price, stock_qty, low_stock_threshold) VALUES
(1, 1, 'Rice 1kg', 'BR123', 60.00, 10, 5),
(2, 1, 'Wheat 1kg', 'BR124', 50.00, 3, 5),
(3, 1, 'Sugar 1kg', 'BR125', 45.00, 20, 5),
(4, 2, 'Paracetamol', 'MD101', 25.00, 50, 10),
(5, 2, 'Cough Syrup', 'MD102', 80.00, 2, 5);

-- Sample data for bills
INSERT INTO bills (bill_id, shopkeeper_id, bill_number, customer_name, customer_contact, bill_date, gst_type, total_amount, payment_status, pdf_file_path) VALUES
(1, 1, 'BILL1001', 'Ramesh', '9000011111', CURDATE(), 'GST', 110.00, 'Paid', NULL),
(2, 1, 'BILL1002', 'Suresh', '9000022222', CURDATE(), 'Non-GST', 60.00, 'Unpaid', NULL),
(3, 2, 'BILL2001', 'Anita', '9000033333', CURDATE(), 'GST', 105.00, 'Partial', NULL);

-- Sample data for bill items
INSERT INTO bill_items (bill_item_id, bill_id, product_id, quantity, price_per_unit, total_price) VALUES
(1, 1, 1, 1, 60.00, 60.00),
(2, 1, 2, 1, 50.00, 50.00),
(3, 2, 1, 1, 60.00, 60.00),
(4, 3, 4, 3, 25.00, 75.00),
(5, 3, 5, 1, 30.00, 30.00);

-- Sample data for documents
INSERT INTO documents (document_id, shopkeeper_id, ca_id, document_name, file_path, uploaded_at) VALUES
(1, 1, 1, 'GST Certificate', 'static/uploads/gst_cert.pdf', NOW()); 