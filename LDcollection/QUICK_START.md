# QUICK START - LDcollection (Simplified)

## 1. Start MySQL (XAMPP)
- Open XAMPP Control Panel
- Click **Start** next to **MySQL**

## 2. Create Database
```bash
mysql -u root -p
CREATE DATABASE ldcollection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

## 3. Configure `.env`
```env
MYSQL_HOST=127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=ldcollection
MYSQL_PORT=3306
SECRET_KEY=ldcollection-secret-key-2024
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

## 4. Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Import Schema
```bash
mysql -u root -p ldcollection < ldcollection.sql
```

## 6. Run
```bash
python app.py
```

Open `http://localhost:5000`.
Admin login: `http://localhost:5000/admin/login`

## Simple Working Flow

1. User visits website
2. User registers or logs in
3. User browses products
4. User adds products to cart
5. User places order
6. Order details are stored in database
7. Admin logs in
8. Admin manages products and orders
