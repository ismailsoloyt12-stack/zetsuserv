#!/usr/bin/env python
"""
Database initialization script for ZetsuServ
This script creates all database tables with proper schema
"""

import os
import sys
import bcrypt
from zetsu import create_app, db
from zetsu.models import AdminUser, User, Request, Message, Notification, OrderProgress

def init_database():
    """Initialize the database with all tables"""
    
    # Remove old database if exists
    db_path = 'zetsuserv.db'
    if os.path.exists(db_path):
        print(f"Removing old database: {db_path}")
        os.remove(db_path)
    
    # Create app and push context
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Verify tables were created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {tables}")
        
        # Verify Request table has all columns
        request_columns = [col['name'] for col in inspector.get_columns('requests')]
        print(f"Request table columns: {request_columns}")
        
        # Check for required columns
        required_columns = ['user_id', 'tracking_code']
        for col in required_columns:
            if col in request_columns:
                print(f"✓ Column '{col}' exists in requests table")
            else:
                print(f"✗ Column '{col}' missing from requests table")
        
        # Create default admin user
        existing_admin = AdminUser.query.filter_by(username='admin').first()
        if not existing_admin:
            print("Creating default admin user...")
            admin_password = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
            admin = AdminUser(
                username='admin',
                email='admin@zetsuserv.com',
                password_hash=admin_password.decode('utf-8')
            )
            db.session.add(admin)
            db.session.commit()
            print("✓ Admin user created (username: admin, password: admin123)")
        else:
            print("✓ Admin user already exists")
        
        print("\n" + "="*50)
        print("✅ Database initialized successfully!")
        print("="*50)
        
        # Print summary
        print("\nDatabase Summary:")
        print(f"- Total tables: {len(tables)}")
        print(f"- Admin users: {AdminUser.query.count()}")
        print(f"- Regular users: {User.query.count()}")
        print(f"- Requests: {Request.query.count()}")
        
        return True

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)