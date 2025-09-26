# Final Deployment Guide for ZetsuServ

This is the complete, error-free deployment guide for your fixed ZetsuServ application.

## Pre-Deployment (Local Machine)

### 1. Commit and Push to GitHub
```bash
git add .
git commit -m "Deploying final AI-fixed version with all enhancements"
git push origin main
```

## Deployment on PythonAnywhere

### 2. Clone Your Project
Open a **new Bash console** on PythonAnywhere and run:

```bash
# Clone your repository
git clone https://github.com/ismailsoloyt12-stack/zetsuserv.git

# Enter the project directory
cd zetsuserv/
```

### 3. Set Up Python Environment
```bash
# Create virtual environment with Python 3.10
python3.10 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# If using MySQL, also install:
pip install pymysql
```

### 4. Create and Configure .env File

**This is the most critical step!**

1. In PythonAnywhere **Files** tab, navigate to `/home/yourusername/zetsuserv/`
2. Create a new file named `.env` (not .env.production!)
3. Add this content and **update with your actual values**:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-generated-secret-key-here

# Database Configuration (choose one)
# For MySQL (recommended):
DATABASE_URL=mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$zetsuserv

# For SQLite (simpler):
# DATABASE_URL=sqlite:////home/yourusername/zetsuserv/instance/zetsuserv.db

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
ADMIN_EMAIL=admin@yourdomain.com
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Initialize Database and Create Admin
Back in the Bash console (with venv activated):

```bash
# Initialize all database tables
python init_database.py

# Create your admin user
flask create-admin
# Or alternatively:
python -m flask create-admin
```

Follow the prompts to set up your admin username and password.

### 6. Configure Web App in PythonAnywhere

Go to the **Web** tab in PythonAnywhere dashboard:

#### A. Source Code
Set to: `/home/yourusername/zetsuserv`

#### B. Virtualenv
Set to: `/home/yourusername/zetsuserv/venv`

#### C. WSGI Configuration File
- Click on the WSGI configuration file path
- **Delete all existing content**
- Replace with this exact code:

```python
import sys
import os

# Add the project directory to the Python path
project_home = '/home/yourusername/zetsuserv'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# CRITICAL: Load environment variables from .env file BEFORE creating the app
from dotenv import load_dotenv
dotenv_path = os.path.join(project_home, '.env')
load_dotenv(dotenv_path)

# Import and create the Flask application instance
from zetsu import create_app
application = create_app(os.getenv('FLASK_ENV', 'production'))
```

**Important:** Replace `yourusername` with your actual PythonAnywhere username!

#### D. Static Files
Click "Enter URL" and "Enter path" to add:
- URL: `/static/`
- Directory: `/home/yourusername/zetsuserv/zetsu/static/`

### 7. Final Steps

1. **Enable Force HTTPS** (in Security section)
2. Click the green **"Reload"** button
3. Your site is now live at: `https://yourusername.pythonanywhere.com`

## Verification Checklist

After deployment, verify these work:

- [ ] Homepage loads without errors
- [ ] `/register` page is accessible
- [ ] `/login` page is accessible
- [ ] `/admin/login` page is accessible
- [ ] Can submit the request form
- [ ] Static files (CSS/JS) load correctly

## Troubleshooting

If you encounter any issues:

### Check Error Logs
Web tab → Error log → View latest

### Common Solutions

**500 Error - Database tables missing:**
```bash
cd ~/zetsuserv
source venv/bin/activate
python init_database.py
```

**Import errors:**
```bash
pip install -r requirements.txt
```

**Admin login not working:**
```bash
flask create-admin
```

## Maintenance Commands

### View Database Status
```bash
flask db-status
```

### List All Admins
```bash
flask list-admins
```

### Reset Admin Password
```bash
flask reset-admin-password
```

### Update Code from GitHub
```bash
cd ~/zetsuserv
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Then reload in Web tab
```

---

## Success! 🎉

Your ZetsuServ application is now deployed and running on PythonAnywhere!

Admin panel: `https://yourusername.pythonanywhere.com/admin/login`
Main site: `https://yourusername.pythonanywhere.com`