# ZetsuServ - Professional Website Development Service

A production-ready Flask web application for a web development service company with client request management system.

## Features

- 🏠 **Professional Landing Page** with services, pricing, and testimonials
- 📝 **Service Request Form** with file upload support
- 🔐 **Admin Dashboard** for managing client requests
- 📊 **Request Status Management** (New, In Progress, Delivered, Closed)
- 📱 **Fully Responsive Design** with RTL support
- 🎨 **Clean, Modern UI** with corporate aesthetics
- 🔒 **Secure Authentication** for admin users
- 📧 **Email Notifications** for new requests

## Technology Stack

- **Backend**: Flask (Python) with Blueprints
- **Database**: SQLAlchemy ORM with SQLite (configurable for PostgreSQL)
- **Frontend**: HTML5, CSS3, JavaScript
- **Templates**: Jinja2
- **Authentication**: Flask-Login with bcrypt
- **Forms**: Flask-WTF with CSRF protection
- **File Uploads**: Secure file handling with validation

## Project Structure

```
zetsuserv/
├── app.py                 # Main application entry point
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── zetsu/
│   ├── __init__.py      # Flask app initialization
│   ├── models.py        # Database models
│   ├── forms.py         # WTForms definitions
│   ├── routes_public.py # Public routes
│   ├── routes_admin.py  # Admin routes
│   ├── templates/       # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── request_form.html
│   │   ├── thanks.html
│   │   └── admin/
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       └── view_request.html
│   └── static/
│       ├── css/
│       │   └── main.css
│       ├── js/
│       │   └── main.js
│       └── uploads/     # Uploaded files directory
└── migrations/          # Database migrations
```

## Installation & Setup

### 1. Clone the repository
```bash
cd zetsuserv
```

### 2. Create virtual environment
```bash
python -m venv venv
```

### 3. Activate virtual environment
- Windows (PowerShell):
```powershell
.\venv\Scripts\Activate
```
- Windows (Command Prompt):
```cmd
venv\Scripts\activate.bat
```
- Linux/Mac:
```bash
source venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Set up environment variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and update with your configuration
```

### 6. Initialize the database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 7. Create admin user
```bash
flask create-admin
```
Follow the prompts to create an admin username and password.

### 8. (Optional) Seed sample data
```bash
flask seed-data
```

### 9. Run the application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Default Routes

- **Public Pages**:
  - `/` - Landing page
  - `/request` - Service request form
  - `/thanks` - Thank you page after submission

- **Admin Pages**:
  - `/admin/login` - Admin login
  - `/admin/dashboard` - Admin dashboard
  - `/admin/request/<id>` - View request details
  - `/admin/logout` - Logout

## Configuration

Edit the `.env` file to configure:

- `SECRET_KEY` - Flask secret key (generate a secure random key)
- `DATABASE_URL` - Database connection string
- `MAIL_*` - Email settings for notifications
- `ADMIN_EMAIL` - Admin email for notifications

## Production Deployment

### Using Gunicorn (Linux/Mac)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Using Waitress (Windows)

```bash
pip install waitress
waitress-serve --port=8000 app:app
```

### Database Migration to PostgreSQL

1. Install PostgreSQL adapter:
```bash
pip install psycopg2-binary
```

2. Update DATABASE_URL in `.env`:
```
DATABASE_URL=postgresql://username:password@localhost:5432/zetsuserv
```

3. Run migrations:
```bash
flask db upgrade
```

### Nginx Configuration (Example)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/zetsuserv/zetsu/static;
    }
}
```

## Security Considerations

- ✅ CSRF protection enabled on all forms
- ✅ Password hashing with bcrypt
- ✅ Secure file upload validation
- ✅ SQL injection prevention with SQLAlchemy ORM
- ✅ XSS protection with Jinja2 auto-escaping
- ✅ Secure session management

## License

This project is proprietary software for ZetsuServ.

## Support

For support, email info@zetsuserv.com

---

Built with ❤️ by ZetsuServ Development Team