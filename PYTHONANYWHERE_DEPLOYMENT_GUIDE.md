# Final Deployment Guide for ZetsuServ on PythonAnywhere

This guide assumes all code fixes have been applied. Follow these steps exactly.

## Prerequisites
- PythonAnywhere account (free or paid)
- GitHub repository with your code
- Gmail account with app-specific password

---

## Step 1: Upload Code to PythonAnywhere

### Option A: Using Git (Recommended)
```bash
cd ~
git clone https://github.com/yourusername/zetsuserv.git
```

### Option B: Manual Upload
1. ZIP your project folder
2. Upload via Files tab
3. Extract: `unzip zetsuserv.zip`

---

## Step 2: Create Virtual Environment

```bash
cd ~/zetsuserv
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If using MySQL, also install:
```bash
pip install pymysql
```

---

## Step 3: Create Your `.env` File

**CRITICAL: This is the most important step!**

1. In PythonAnywhere Files tab, navigate to `/home/yourusername/zetsuserv/`
2. Create a new file named `.env` (NOT `.env.production`)
3. Copy the content from `.env.production` template
4. Update these values:

```env
# Replace with a secure random key
SECRET_KEY=generate-using-python-command-below

# For SQLite (easier to start)
DATABASE_URL=sqlite:////home/YOURUSERNAME/zetsuserv/instance/zetsuserv.db

# For MySQL (if you set it up)
# DATABASE_URL=mysql+pymysql://YOURUSERNAME:YOURPASSWORD@YOURUSERNAME.mysql.pythonanywhere-services.com/YOURUSERNAME$zetsuserv

# Your actual Gmail
MAIL_USERNAME=your.email@gmail.com
# App-specific password from Google
MAIL_PASSWORD=your-16-char-app-password
MAIL_DEFAULT_SENDER=your.email@gmail.com

# Admin email for notifications
ADMIN_EMAIL=your.email@gmail.com
```

Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 4: Initialize Database

**CRITICAL: This step MUST be done or you'll get 500 errors!**

```bash
cd ~/zetsuserv
source venv/bin/activate

# Method 1: Use the initialization script (RECOMMENDED)
python init_database.py

# Method 2: Use Flask-Migrate (if Method 1 fails)
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create admin user (REQUIRED)
flask create-admin
```

**Verify tables were created:**
```bash
# For MySQL
mysql -u YOURUSERNAME -p 'YOURUSERNAME$zetsuserv' -e "SHOW TABLES;"

# For SQLite
sqlite3 ~/zetsuserv/instance/zetsuserv.db ".tables"
```

---

## Step 5: Configure Web App

1. Go to Web tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select Python 3.10

### Configure WSGI File

1. Click on "WSGI configuration file"
2. Delete ALL content
3. Replace with:

```python
import sys
import os

# Add project to path
project_home = '/home/YOURUSERNAME/zetsuserv'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables
from dotenv import load_dotenv
dotenv_path = os.path.join(project_home, '.env')
load_dotenv(dotenv_path)

# Set production environment
os.environ['FLASK_ENV'] = 'production'

# Import app
from zetsu import create_app
application = create_app('production')
```

**Replace `YOURUSERNAME` with your PythonAnywhere username!**

### Set Virtual Environment

In Web tab, Virtualenv section:
```
/home/YOURUSERNAME/zetsuserv/venv
```

### Configure Static Files

Add this mapping:
- URL: `/static/`
- Directory: `/home/YOURUSERNAME/zetsuserv/zetsu/static/`

### Set Working Directory

In Web tab:
```
/home/YOURUSERNAME/zetsuserv
```

---

## Step 6: Final Steps

1. Enable "Force HTTPS" in Security section
2. Click the green "Reload" button
3. Visit: `https://YOURUSERNAME.pythonanywhere.com`

---

## Troubleshooting

### Check Error Log
Web tab → Error log → View latest errors

### Common Issues

**Import Error:**
- Check WSGI file has correct username
- Verify virtual environment path

**Database Error:**
```bash
cd ~/zetsuserv
source venv/bin/activate
flask db upgrade
```

**Email Not Sending:**
- Verify Gmail app-specific password
- Check MAIL_USERNAME in .env

**500 Error:**
- Check .env file exists and has all values
- Look at error log for details

---

## Testing Checklist

- [ ] Homepage loads
- [ ] Admin login works (`/admin/login`)
- [ ] Request form submits
- [ ] Email notifications send
- [ ] Static files load (CSS/JS)

---

## Maintenance

### Update Code
```bash
cd ~/zetsuserv
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
```
Then reload in Web tab.

### Backup Database
```bash
# SQLite
cp ~/zetsuserv/instance/zetsuserv.db ~/backup_$(date +%Y%m%d).db

# MySQL
mysqldump -u USERNAME -p 'USERNAME$zetsuserv' > backup.sql
```

---

## Important Notes

1. **SECRET_KEY must be changed** - Never use default
2. **Gmail needs app-specific password** - Not your regular password
3. **Check error logs first** when troubleshooting
4. **Free tier sleeps after 3 months** - Visit monthly to keep active

---

## Success!
Your app should now be live at `https://YOURUSERNAME.pythonanywhere.com`

If you encounter issues, check:
1. Error log (Web tab)
2. .env file has all values
3. Database is initialized
4. Virtual environment is activated