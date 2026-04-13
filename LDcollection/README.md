# LDcollection - Simple E-Commerce Demo

A lightweight Flask + MySQL demo store with a clean UI, product list, cart, and checkout.

## Features

- Browse products
- Add items to cart (session-based)
- Simple checkout (guest)
- Order confirmation page
- Admin login system
- Admin dashboard (orders, revenue, stock)

## Simple Working Flow

1. User visits website
2. User registers or logs in
3. User browses products
4. User adds products to cart
5. User places order
6. Order details are stored in database
7. Admin logs in
8. Admin manages products and orders

## Tech Stack

- Backend: Flask
- Database: MySQL (mysql-connector-python)
- Frontend: HTML + CSS

## Setup (XAMPP)

1. Start MySQL in XAMPP
   - Open XAMPP Control Panel
   - Click **Start** next to **MySQL**

2. Create the database (XAMPP Shell)
   ```bash
   mysql -u root -p
   CREATE DATABASE ldcollection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   EXIT;
   ```

3. Configure `.env`
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

4. Install dependencies
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. Load the schema + sample data
   ```bash
   mysql -u root -p ldcollection < ldcollection.sql
   ```

6. Run the app
   ```bash
   python app.py
   ```

Visit `http://localhost:5000`.

Admin login: `http://localhost:5000/admin/login`

## Project Structure

```
app.py
requirements.txt
templates/
static/css/style.css
ldcollection.sql
```

## Notes

- Cart is stored in session (no customer accounts).
- Orders are saved in MySQL.
- Change `ADMIN_PASSWORD` in `.env` for production use.
