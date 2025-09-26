# ZetsuServ PythonAnywhere Deployment Guide

This guide will walk you through deploying ZetsuServ on PythonAnywhere step by step.

## Prerequisites

1. A PythonAnywhere account (free tier is sufficient to start)
2. Your ZetsuServ project files
3. Basic knowledge of using the terminal/console

## Step 1: Create PythonAnywhere Account

1. Go to [PythonAnywhere](https://www.pythonanywhere.com)
2. Sign up for a free account (or paid if you need custom domain)
3. Remember your username - you'll need it throughout the setup

## Step 2: Upload Your Project

### Option A: Using Git (Recommended)

1. Open a Bash console in PythonAnywhere
2. Clone your repository:
   ```bash
   cd ~
   git clone https://github.com/yourusername/zetsuserv.git
   ```

### Option B: Manual Upload

1. ZIP your entire project folder on your local machine
2. Upload via PythonAnywhere's Files tab
3. Extract in Bash console:
   ```bash
   cd ~
   unzip zetsuserv.zip
   ```

## Step 3: Set Up Virtual Environment

1. Open a Bash console in PythonAnywhere
2. Create virtual environment:
   ```bash
   cd ~/zetsuserv
   python3.10 -m venv venv
   ```
3. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

## Step 4: Install Dependencies

1. Ensure you're in the project directory with virtual environment activated:
   ```bash
   cd ~/zetsuserv
   source venv/bin/activate
   ```
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. If using MySQL, also install:
   ```bash
   pip install pymysql
   ```

## Step 5: Configure Environment Variables

1. Copy the production environment template:
   ```bash
   cp .env.production .env
   ```
2. Edit the .env file:
   ```bash
   nano .env
   ```
3. Update these critical values:
   - `SECRET_KEY`: Generate a secure random key
     ```python
     # Run this in Python console to generate a key:
     import secrets
     print(secrets.token_hex(32))
     ```
   - `DATABASE_URL`: Choose one:
     - For SQLite: `sqlite:////home/yourusername/zetsuserv/instance/zetsuserv.db`
     - For MySQL: See Step 6
   - Email settings (for Gmail):
     - `MAIL_USERNAME`: Your Gmail address
     - `MAIL_PASSWORD`: Your app-specific password (not regular password)
     - `ADMIN_EMAIL`: Where to receive admin notifications

## Step 6: Database Setup

### Option A: Using SQLite (Simpler)

1. Create the database:
   ```bash
   cd ~/zetsuserv
   source venv/bin/activate
   python -m flask db init
   python -m flask db migrate -m "Initial migration"
   python -m flask db upgrade
   ```

### Option B: Using MySQL (Better for production)

1. Go to the Databases tab in PythonAnywhere
2. Create a MySQL database (note the credentials)
3. Update .env with MySQL connection:
   ```
   DATABASE_URL=mysql+pymysql://yourusername:yourpassword@yourusername.mysql.pythonanywhere-services.com/yourusername$zetsuserv
   ```
4. Initialize database:
   ```bash
   cd ~/zetsuserv
   source venv/bin/activate
   python -m flask db init
   python -m flask db migrate -m "Initial migration"
   python -m flask db upgrade
   ```

## Step 7: Create Admin User

1. Run the admin creation command:
   ```bash
   cd ~/zetsuserv
   source venv/bin/activate
   python -m flask create-admin
   ```
2. Follow the prompts to set admin username and password

## Step 8: Configure Web App

1. Go to the Web tab in PythonAnywhere
2. Click "Add a new web app"
3. Choose "Manual configuration" (not Flask)
4. Select Python 3.10

### Configure WSGI File

1. Click on the WSGI configuration file link
2. Delete all existing content
3. Add this code:
   ```python
   import sys
   import os
   
   # Update this with your username
   project_home = '/home/yourusername/zetsuserv'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)
   
   # Load environment variables
   from dotenv import load_dotenv
   env_path = os.path.join(project_home, '.env')
   load_dotenv(env_path)
   
   os.environ['FLASK_ENV'] = 'production'
   
   from app import application
   ```
4. Replace `yourusername` with your PythonAnywhere username

### Configure Virtual Environment

1. In the Web tab, find "Virtualenv" section
2. Enter the path: `/home/yourusername/zetsuserv/venv`

### Configure Static Files

1. In the Static files section, add:
   - URL: `/static/`
   - Directory: `/home/yourusername/zetsuserv/zetsu/static/`

## Step 9: Final Configuration

### Set Working Directory

1. In the Web tab, find "Working directory" section
2. Set it to: `/home/yourusername/zetsuserv`

### Enable Force HTTPS (Recommended)

1. In the Web tab, find "Security" section
2. Enable "Force HTTPS"

## Step 10: Launch Your Site

1. Click the green "Reload" button in the Web tab
2. Click on your site URL to test
3. Check the error log if there are issues

## Testing Your Deployment

1. Visit your site: `https://yourusername.pythonanywhere.com`
2. Test key features:
   - Homepage loads correctly
   - Admin login works
   - Form submissions work
   - Email notifications are sent (if configured)

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors
- **Solution**: Check that your virtual environment path is correct
- Verify wsgi.py has the correct project path

#### 2. Database Errors
- **Solution**: Ensure database is initialized:
  ```bash
  python -m flask db upgrade
  ```

#### 3. Static Files Not Loading
- **Solution**: Check static files mapping in Web tab
- Ensure path ends with `/`

#### 4. Email Not Sending
- **Solution**: 
  - For Gmail, use app-specific password
  - Check firewall isn't blocking SMTP

#### 5. 500 Internal Server Error
- **Solution**: Check error log in Web tab
- Common cause: Missing environment variables

### Checking Logs

1. Go to Web tab
2. Check these logs:
   - Error log (most important)
   - Server log
   - Access log

## Maintenance Tasks

### Updating Code

1. Pull latest changes:
   ```bash
   cd ~/zetsuserv
   git pull origin main
   ```
2. Update dependencies:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   python -m flask db upgrade
   ```
4. Reload web app in Web tab

### Database Backup

For SQLite:
```bash
cp ~/zetsuserv/instance/zetsuserv.db ~/zetsuserv/instance/backup_$(date +%Y%m%d).db
```

For MySQL:
```bash
mysqldump -u yourusername -p'yourpassword' -h yourusername.mysql.pythonanywhere-services.com 'yourusername$zetsuserv' > backup_$(date +%Y%m%d).sql
```

### Monitoring

1. Check error logs regularly
2. Monitor disk usage in Files tab
3. Check database size in Databases tab

## Performance Optimization

### For Free Tier

1. Minimize static file sizes
2. Use CDN for large assets
3. Optimize database queries

### For Paid Tiers

1. Enable always-on tasks
2. Increase worker processes
3. Use MySQL instead of SQLite
4. Enable caching

## Security Checklist

- [ ] Changed SECRET_KEY from default
- [ ] Enabled Force HTTPS
- [ ] Set secure admin password
- [ ] Configured secure email password
- [ ] Regular backups scheduled
- [ ] Error logs monitored

## Getting Help

1. PythonAnywhere Forums: https://www.pythonanywhere.com/forums/
2. Check error logs first
3. PythonAnywhere Help: https://help.pythonanywhere.com/

## Next Steps

1. Configure custom domain (paid accounts)
2. Set up SSL certificate
3. Implement automated backups
4. Set up monitoring alerts
5. Configure CDN for better performance

---

**Important Notes:**
- Free tier has limitations (1 web app, 512MB disk space)
- Site goes to sleep after 3 months of inactivity on free tier
- Always test changes in development before deploying
- Keep your `.env` file secure and never commit it to Git



e7041cf81778b2b868ce1aef5329e08d456bbb51ce2970a764af99f9fe8fe4ad