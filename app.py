import os
import sys

# Add the project directory to the Python path for PythonAnywhere
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from zetsu import create_app, db
from zetsu.models import AdminUser
import bcrypt

# Create the Flask app with appropriate configuration
flask_env = os.getenv('FLASK_ENV', 'production')
app = create_app(flask_env)
application = app  # For WSGI servers like PythonAnywhere

@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')

@app.cli.command()
def create_admin():
    """Create default admin user."""
    from getpass import getpass
    
    username = input('Enter admin username (default: admin): ') or 'admin'
    email = input('Enter admin email (default: admin@zetsuserv.com): ') or 'admin@zetsuserv.com'
    password = getpass('Enter admin password: ')
    
    if not password:
        print('Password is required!')
        return
    
    # Check if admin already exists
    existing_admin = AdminUser.query.filter_by(username=username).first()
    if existing_admin:
        print(f'Admin user {username} already exists!')
        return
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Create admin user
    admin = AdminUser(
        username=username,
        email=email,
        password_hash=password_hash.decode('utf-8')
    )
    
    db.session.add(admin)
    db.session.commit()
    
    print(f'Admin user {username} created successfully!')

@app.cli.command()
def seed_data():
    """Seed sample data for testing."""
    from zetsu.models import Request
    from datetime import datetime, timedelta
    import json
    
    # Create sample requests
    sample_requests = [
        {
            'client_name': 'John Smith',
            'client_email': 'john@example.com',
            'phone': '+1234567890',
            'project_title': 'Corporate Website',
            'project_type': 'business',
            'pages_required': 5,
            'budget': '$5000-$10000',
            'details': 'Need a professional corporate website with modern design.',
            'status': 'new',
            'created_at': datetime.now() - timedelta(days=2)
        },
        {
            'client_name': 'Sarah Johnson',
            'client_email': 'sarah@example.com',
            'phone': '+0987654321',
            'project_title': 'E-commerce Platform',
            'project_type': 'ecommerce',
            'pages_required': 15,
            'budget': '$15000-$25000',
            'details': 'Full e-commerce solution with payment integration.',
            'status': 'in_progress',
            'created_at': datetime.now() - timedelta(days=5)
        },
        {
            'client_name': 'Ahmed Ali',
            'client_email': 'ahmed@example.com',
            'phone': '+9876543210',
            'project_title': 'Portfolio Landing Page',
            'project_type': 'landing',
            'pages_required': 1,
            'budget': '$500-$1000',
            'details': 'Simple but elegant portfolio landing page.',
            'status': 'delivered',
            'created_at': datetime.now() - timedelta(days=10)
        }
    ]
    
    for req_data in sample_requests:
        request = Request(**req_data)
        db.session.add(request)
    
    db.session.commit()
    print('Sample data seeded successfully!')


@app.cli.command()
def send_test_email():
    """Send a test email using current configuration to ADMIN_EMAIL.
    Usage: python -m flask send-test-email
    """
    from flask import current_app
    try:
        from flask_mail import Message as MailMessage, Mail
    except ImportError:
        print('Flask-Mail is not installed. Please install it first: pip install Flask-Mail')
        return

    with app.app_context():
        mail = Mail(current_app)
        username = current_app.config.get('MAIL_USERNAME')
        server = current_app.config.get('MAIL_SERVER')
        port = current_app.config.get('MAIL_PORT')
        use_tls = current_app.config.get('MAIL_USE_TLS')
        use_ssl = current_app.config.get('MAIL_USE_SSL')
        recipient = current_app.config.get('ADMIN_EMAIL')
        
        if not username:
            print('MAIL_USERNAME is not configured. Set it in your .env (your Gmail address).')
            return
        if not recipient:
            print('ADMIN_EMAIL not set. Please set ADMIN_EMAIL in .env to receive the test email.')
            return
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or username
        if str(server).endswith('gmail.com'):
            sender_email = username
        
        try:
            msg = MailMessage(
                subject='ZetsuServ Test Email',
                sender=sender_email,
                recipients=[recipient],
                body=(
                    f'This is a test email from ZetsuServ.\n\n'
                    f'Server: {server}:{port} TLS={use_tls} SSL={use_ssl}\n'
                    f'Username: {username}\n'
                    f'Sender: {sender_email}\n'
                ),
            )
            mail.send(msg)
            print(f'Test email sent to {recipient} successfully using {server}:{port} as {username}.')
        except Exception as e:
            print('Failed to send test email:', e)

# Development server (not used in production)
if __name__ == '__main__':
    # Only run in development mode
    if app.config.get('DEBUG', False):
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        print("This script should not be run directly in production.")
        print("Use a WSGI server like gunicorn or PythonAnywhere's built-in server.")
