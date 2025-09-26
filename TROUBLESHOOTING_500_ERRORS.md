# Troubleshooting 500 Errors on PythonAnywhere

## Most Common Cause: Database Tables Don't Exist

The #1 reason for 500 errors after deployment is **missing database tables**. The error logs show messages like:
- `Table 'Zetsuserv$default.users' doesn't exist`
- `no such table: users`
- `no such table: requests`

## ✅ Quick Fix Solution

### Step 1: Connect to PythonAnywhere Console
```bash
cd ~/zetsuserv
source venv/bin/activate
```

### Step 2: Check Your .env File
```bash
cat .env | grep DATABASE_URL
```
Make sure DATABASE_URL is set correctly:
- For MySQL: `mysql+pymysql://username:password@username.mysql.pythonanywhere-services.com/username$zetsuserv`
- For SQLite: `sqlite:////home/username/zetsuserv/instance/zetsuserv.db`

### Step 3: Initialize the Database
```bash
# Method 1: Use our initialization script
python init_database.py

# If that fails, Method 2: Manual initialization
python
>>> from zetsu import create_app, db
>>> app = create_app('production')
>>> with app.app_context():
...     db.create_all()
...     print("Tables created!")
>>> exit()
```

### Step 4: Verify Tables Were Created

For MySQL:
```bash
mysql -u YOURUSERNAME -p
# Enter password
USE YOURUSERNAME$zetsuserv;
SHOW TABLES;
```

For SQLite:
```bash
sqlite3 ~/zetsuserv/instance/zetsuserv.db
.tables
.exit
```

### Step 5: Create Admin User
```bash
flask create-admin
```

### Step 6: Reload Web App
Go to PythonAnywhere Web tab → Click "Reload"

---

## Other Common 500 Error Causes

### 1. F-String Syntax Errors
**Error:** `SyntaxError: f-string expression part cannot include a backslash`

**Solution:** Already fixed in latest code. Pull latest changes:
```bash
git pull origin main
```

### 2. Indentation Errors
**Error:** `IndentationError: unexpected indent`

**Solution:** Already fixed in latest code. Pull latest changes.

### 3. Missing Environment Variables
**Error:** Various database connection errors

**Solution:** Check your .env file has all required values:
```bash
cat .env
```

Required variables:
- SECRET_KEY (generate new one!)
- DATABASE_URL
- MAIL_USERNAME
- MAIL_PASSWORD
- ADMIN_EMAIL

### 4. Import Errors
**Error:** `ImportError` or module not found

**Solution:** Reinstall dependencies:
```bash
cd ~/zetsuserv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Permission Issues
**Error:** Cannot write to database file (SQLite)

**Solution:** Ensure instance directory exists and is writable:
```bash
mkdir -p ~/zetsuserv/instance
chmod 755 ~/zetsuserv/instance
```

---

## Debugging Steps

### 1. Check Error Log
PythonAnywhere Web tab → Error log → View latest

### 2. Test in Console
```bash
cd ~/zetsuserv
source venv/bin/activate
python
>>> from zetsu import create_app
>>> app = create_app('production')
>>> # If this works, app loads correctly
```

### 3. Test Database Connection
```bash
python
>>> from zetsu import create_app, db
>>> app = create_app('production')
>>> with app.app_context():
...     db.engine.execute("SELECT 1")
>>> # If this works, database connects
```

### 4. Check Flask-Migrate Status
```bash
flask db current
# Shows current migration version

flask db heads
# Shows latest migration version
```

---

## Complete Reset (Last Resort)

If nothing works, do a complete reset:

### For SQLite:
```bash
rm -f ~/zetsuserv/instance/zetsuserv.db
cd ~/zetsuserv
source venv/bin/activate
python init_database.py
flask create-admin
```

### For MySQL:
```bash
mysql -u YOURUSERNAME -p
DROP DATABASE IF EXISTS `YOURUSERNAME$zetsuserv`;
CREATE DATABASE `YOURUSERNAME$zetsuserv`;
exit;

cd ~/zetsuserv
source venv/bin/activate
python init_database.py
flask create-admin
```

Then reload in Web tab.

---

## Prevention Tips

1. **Always initialize database** after deployment
2. **Test locally first** with production settings
3. **Check error logs immediately** after deployment
4. **Keep .env file updated** with correct values
5. **Use init_database.py** for consistent setup

---

## Getting Help

If still having issues:

1. Check the full error in PythonAnywhere error log
2. Look for the specific error message in this guide
3. Post on PythonAnywhere forums with:
   - Full error traceback
   - Your .env contents (hide passwords!)
   - Output of `pip freeze`

---

## Success Checklist

After fixing, verify:
- [ ] Homepage loads without error
- [ ] Can access /register page
- [ ] Can access /login page
- [ ] Can submit request form
- [ ] Admin login works at /admin/login

If all work, your 500 errors are resolved! 🎉