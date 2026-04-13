# Database Setup (Simplified)

This project uses a small MySQL schema with four tables: `product`, `order`, `order_item`, and `admin_user`.

## Quick Setup

1. Start MySQL (XAMPP)
2. Create the database
   ```bash
   mysql -u root -p
   CREATE DATABASE ldcollection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   EXIT;
   ```
3. Import the schema + sample data
   ```bash
   mysql -u root -p ldcollection < ldcollection.sql
   ```

## Verify

```bash
mysql -u root -p ldcollection
SHOW TABLES;
SELECT COUNT(*) FROM product;
EXIT;
```

## Tables

- `product`: catalog items
- `order`: checkout records
- `order_item`: items per order
- `admin_user`: admin login accounts
