-- -- Update bill_date column from date to datetime to preserve time information
-- ALTER TABLE `bills` MODIFY COLUMN `bill_date` datetime NOT NULL;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id VARCHAR(50) NOT NULL COMMENT 'Reference to users.user_id',
    receiver_id VARCHAR(50) NOT NULL COMMENT 'Reference to users.user_id', 
    message TEXT NOT NULL COMMENT 'Message content (max 2000 chars enforced in app)',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When message was sent',
    bill_id INT NULL COMMENT 'Reference to bills.bill_id for bill remarks',
    message_type VARCHAR(10) DEFAULT 'chat' COMMENT 'Type: chat or remark',
    `read` BOOLEAN DEFAULT FALSE COMMENT 'Whether message has been read by receiver',
    
    -- Performance indexes
    INDEX idx_conversation (sender_id, receiver_id, timestamp),
    INDEX idx_unread_messages (receiver_id, `read`, timestamp),
    INDEX idx_bill_messages (bill_id, message_type),
    INDEX idx_sender_messages (sender_id, timestamp),
    
    -- Foreign key constraints
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE SET NULL
);

SHOW INDEX FROM messages;

-- Add the missing unread_messages index if it doesn't exist
CREATE INDEX idx_unread_messages ON messages (receiver_id, `read`, timestamp);

-- Verify the index was created
SHOW INDEX FROM messages;