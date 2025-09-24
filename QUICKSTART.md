# 🚀 ZetsuServ Quick Start Guide

## Installation Complete! ✅

Your ZetsuServ application is now ready to run. Follow these simple steps:

## 📋 Prerequisites Installed
- ✅ Python 3.x
- ✅ Virtual environment activated
- ✅ All dependencies installed
- ✅ Database initialized

## 🔧 Running the Application

### Option 1: Using the Start Script (Recommended)
```bash
python start.py
```

This will:
- Initialize the database (if needed)
- Create a default admin user (if none exists)
- Start the Flask server

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`
- ⚠️ Please change the password after first login!

### Option 2: Using Flask Commands
```bash
# Set environment variable
$env:FLASK_APP = "app.py"

# Run the application
python -m flask run
```

### Option 3: Direct Python
```bash
python app.py
```

## 🌐 Access Points

Once the server is running, you can access:

| Page | URL | Description |
|------|-----|-------------|
| **Home Page** | http://localhost:5000 | Main landing page with services |
| **Request Service** | http://localhost:5000/request | Submit a service request |
| **Admin Login** | http://localhost:5000/admin/login | Admin dashboard login |
| **Admin Dashboard** | http://localhost:5000/admin/dashboard | Manage requests (requires login) |

## 🔑 Admin Features

After logging in to the admin panel, you can:
- View all client requests
- Filter requests by status (New, In Progress, Delivered, Closed)
- Update request status
- View client details and uploaded files
- Delete requests

## 🧪 Testing the Application

1. **Test the Request Form:**
   - Go to http://localhost:5000/request
   - Fill in the form with sample data
   - Upload a test file (optional)
   - Submit and check the confirmation page

2. **Test Admin Panel:**
   - Login at http://localhost:5000/admin/login
   - View the submitted request in the dashboard
   - Click on the request to see details
   - Update the status and verify changes

## 📝 Sample Data

To add sample data for testing:
```bash
python -m flask seed-data
```

## 🛑 Stopping the Server

Press `Ctrl+C` in the terminal to stop the Flask server.

## 🔧 Troubleshooting

If you encounter any issues:

1. **Port already in use:**
   - Change the port in `app.py` (last line)
   - Or use: `python app.py --port 5001`

2. **Database errors:**
   ```bash
   # Delete the database and recreate
   del zetsuserv.db
   python start.py
   ```

3. **Module not found:**
   ```bash
   # Ensure virtual environment is activated
   .\venv\Scripts\Activate
   pip install -r requirements.txt
   ```

## 📧 Email Configuration (Optional)

To enable email notifications for new requests:

1. Edit `.env` file (copy from `.env.example`)
2. Add your email settings:
   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

## 🎉 Ready to Go!

Your ZetsuServ application is now up and running. Enjoy exploring all the features!

---
Need help? Check the main README.md for detailed documentation.