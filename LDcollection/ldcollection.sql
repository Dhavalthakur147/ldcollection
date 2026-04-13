-- LDcollection MySQL Database Schema and Sample Data (Normalized)
-- Database: ldcollection

CREATE DATABASE IF NOT EXISTS `ldcollection` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `ldcollection`;

-- =====================================================
-- CREATE TABLES
-- =====================================================

CREATE TABLE IF NOT EXISTS `category` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(80) NOT NULL UNIQUE,
  `description` VARCHAR(255),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_category_name (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `full_name` VARCHAR(120) NOT NULL,
  `email` VARCHAR(160) NOT NULL UNIQUE,
  `phone` VARCHAR(40),
  `default_address` VARCHAR(255),
  `password_hash` VARCHAR(255),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_email (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `product` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(120) NOT NULL,
  `description` LONGTEXT,
  `price` FLOAT NOT NULL,
  `category_id` INT NOT NULL,
  `stock` INT DEFAULT 0,
  `image_url` VARCHAR(255),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`category_id`) REFERENCES `category`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_product_category_id (`category_id`),
  INDEX idx_product_name (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `order` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_number` VARCHAR(50) UNIQUE NOT NULL,
  `user_id` INT NOT NULL,
  `shipping_address` VARCHAR(255) NOT NULL,
  `total_amount` FLOAT NOT NULL,
  `status` VARCHAR(20) DEFAULT 'pending',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_order_number (`order_number`),
  INDEX idx_order_status (`status`),
  INDEX idx_order_user_id (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `order_item` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `order_id` INT NOT NULL,
  `product_id` INT NOT NULL,
  `quantity` INT NOT NULL,
  `price` FLOAT NOT NULL,
  FOREIGN KEY (`order_id`) REFERENCES `order`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`product_id`) REFERENCES `product`(`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  INDEX idx_order_item_order_id (`order_id`),
  INDEX idx_order_item_product_id (`product_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `admin_user` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(100) UNIQUE NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- INSERT SAMPLE DATA
-- =====================================================

INSERT INTO `category` (`name`, `description`) VALUES
('Dresses', 'Elegant and casual dresses'),
('Shirts', 'Classic shirts for all occasions'),
('Jeans', 'Denim wear collection'),
('Sweaters', 'Warm and stylish sweaters'),
('Jackets', 'Outerwear for all seasons'),
('Pants', 'Comfortable and practical pants'),
('Hoodies', 'Casual hooded sweatshirts');

INSERT INTO `user` (`full_name`, `email`, `phone`, `default_address`) VALUES
('Aarav Shah', 'aarav.shah@example.com', '+91-9876543210', '12 Lake View Road, Ahmedabad'),
('Mira Patel', 'mira.patel@example.com', '+91-9988776655', '45 MG Road, Surat');

INSERT INTO `product` (`name`, `description`, `price`, `category_id`, `stock`, `image_url`) VALUES
('Elegant Black Dress', 'A sophisticated black dress perfect for any occasion', 49.99, 1, 20, 'https://via.placeholder.com/300x400?text=Black+Dress'),
('Classic White Shirt', 'Timeless white shirt for everyday wear', 29.99, 2, 30, 'https://via.placeholder.com/300x400?text=White+Shirt'),
('Blue Denim Jeans', 'Comfortable and stylish denim jeans', 59.99, 3, 25, 'https://via.placeholder.com/300x400?text=Jeans'),
('Summer Floral Dress', 'Colorful floral dress for summer', 45.99, 1, 15, 'https://via.placeholder.com/300x400?text=Floral+Dress'),
('Red Sweater', 'Cozy red sweater for cooler days', 39.99, 4, 18, 'https://via.placeholder.com/300x400?text=Red+Sweater'),
('Black Leather Jacket', 'Classic black leather jacket', 129.99, 5, 10, 'https://via.placeholder.com/300x400?text=Jacket'),
('Grey Cargo Pants', 'Practical cargo pants with multiple pockets', 54.99, 6, 22, 'https://via.placeholder.com/300x400?text=Cargo+Pants'),
('Pink Hoodie', 'Comfortable pink hoodie', 44.99, 7, 20, 'https://via.placeholder.com/300x400?text=Pink+Hoodie');

INSERT INTO `order` (`order_number`, `user_id`, `shipping_address`, `total_amount`, `status`) VALUES
('ORD-2026-0001', 1, '12 Lake View Road, Ahmedabad', 109.98, 'pending'),
('ORD-2026-0002', 2, '45 MG Road, Surat', 59.99, 'confirmed');

INSERT INTO `order_item` (`order_id`, `product_id`, `quantity`, `price`) VALUES
(1, 1, 1, 49.99),
(1, 2, 2, 29.99),
(2, 3, 1, 59.99);

-- =====================================================
-- VERIFY INSTALLATION
-- =====================================================

SELECT 'Tables Created Successfully!' AS status;
SELECT COUNT(*) AS total_categories FROM `category`;
SELECT COUNT(*) AS total_users FROM `user`;
SELECT COUNT(*) AS total_products FROM `product`;
SELECT COUNT(*) AS total_orders FROM `order`;
