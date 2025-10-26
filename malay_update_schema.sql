-- Update bill_date column from date to datetime to preserve time information
ALTER TABLE `bills` MODIFY COLUMN `bill_date` datetime NOT NULL;