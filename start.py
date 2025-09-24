#!/usr/bin/env python
"""
ZetsuServ Quick Start Script
This script initializes the database and starts the Flask application.
"""

import os
import sys
from zetsu import create_app, db
import bcrypt

def initialize_database(app):
    """Check if database exists."""
    import os
    # Check both possible database locations
    db_paths = ['zetsuserv.db', 'instance/zetsuserv.db']
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"✓ Database found at {db_path}!")
            return True
    
    print("⚠️  Database not found. Creating new database...")
    with app.app_context():
        db.create_all()
        print("✓ Database created successfully!")
    return True

def create_default_admin(app):
    """Create a default admin user if none exists."""
    with app.app_context():
        # Import models here after app context is established
        from zetsu.models import AdminUser
        # Check if any admin exists
        admin_count = AdminUser.query.count()
        if admin_count == 0:
            print("\n📝 No admin user found. Creating default admin...")
            
            # Create default admin
            username = "admin"
            email = "admin@zetsuserv.com"
            password = "admin123"  # Default password
            
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            admin = AdminUser(
                username=username,
                email=email,
                password_hash=password_hash.decode('utf-8')
            )
            
            db.session.add(admin)
            db.session.commit()
            
            print(f"✓ Admin user created successfully!")
            print(f"  Username: {username}")
            print(f"  Password: {password}")
            print(f"  ⚠️  Please change the password after first login!")
        else:
            print("✓ Admin user already exists")

def main():
    """Main function to start the application."""
    print("=" * 50)
    print(" ZetsuServ - Professional Web Development Service")
    print("=" * 50)
    print()
    
    # Create Flask app
    app = create_app('development')
    
    # Check database
    print("🔧 Checking database...")
    if not initialize_database(app):
        print("\nPlease initialize the database first by running:")
        print("  python init_db.py")
        return
    
    # Check for admin user
    print("\n🚀 Starting Flask server...")
    print("📌 Application URL: http://localhost:5000")
    print("🔐 Admin Panel: http://localhost:5000/admin/login")
    print("\nPress CTRL+C to stop the server\n")
    print("-" * 50)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
        sys.exit(0)