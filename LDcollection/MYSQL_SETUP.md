# MySQL Setup (Simplified)

## 1. Start MySQL (XAMPP)

- Open XAMPP Control Panel
- Click **Start** next to **MySQL**

## 2. Create Database (XAMPP Shell)

```bash
mysql -u root -p
```

```sql
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

## 4. Import Schema

```bash
mysql -u root -p ldcollection < ldcollection.sql
```

## 5. Run the App

```bash
python app.py
```

Admin login: `http://localhost:5000/admin/login`

## Troubleshooting

- Connection error: MySQL not running or wrong credentials
- Unknown database: create `ldcollection` first
- Module error: run `pip install -r requirements.txt`
