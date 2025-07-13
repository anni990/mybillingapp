ALTER TABLE shopkeepers ADD COLUMN gst_doc_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN pan_doc_path VARCHAR(255);
ALTER TABLE shopkeepers ADD COLUMN address_proof_path VARCHAR(255);

ALTER TABLE users ADD COLUMN plain_password VARCHAR(255);

ALTER TABLE chartered_accountants ADD COLUMN gst_number VARCHAR(255);
ALTER TABLE chartered_accountants ADD COLUMN pan_number VARCHAR(255);
ALTER TABLE chartered_accountants ADD COLUMN address VARCHAR(255);
