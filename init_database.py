#!/usr/bin/env python
"""
Database initialization script for PythonAnywhere deployment.
Run this after setting up your .env file to create all database tables.
"""

import os
import sys
from pathlib import Path

# Add project to path
project_home = Path(__file__).resolve().parent
sys.path.insert(0, str(project_home))

# Load environment variables
from dotenv import load_dotenv
env_path = project_home / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}")
else:
    print(f"ERROR: No .env file found at {env_path}")
    print("Please create your .env file first!")
    sys.exit(1)

# Set Flask environment
os.environ['FLASK_ENV'] = os.getenv('FLASK_ENV', 'production')

# Import Flask app and database
from zetsu import create_app, db
from zetsu.models import User, AdminUser, Request, Message, Notification, OrderProgress

def init_database():
    """Initialize the database with all tables."""
    
    print("\n=== Database Initialization ===\n")
    
    # Create app
    app = create_app(os.getenv('FLASK_ENV', 'production'))
    
    with app.app_context():
        # Get database URL for display (hide password)
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'mysql' in db_url:
            # MySQL database
            parts = db_url.split('@')
            if len(parts) > 1:
                db_display = parts[0].split('://')[0] + '://[HIDDEN]@' + parts[1]
            else:
                db_display = db_url
            print(f"Database Type: MySQL")
        else:
            # SQLite database
            db_display = db_url
            print(f"Database Type: SQLite")
        
        print(f"Database URL: {db_display}")
        
        try:
            # Create all tables
            print("\nCreating database tables...")
            db.create_all()
            
            # Verify tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n✓ Successfully created {len(tables)} tables:")
            for table in sorted(tables):
                print(f"  - {table}")
            
            # Check if admin exists
            admin_count = AdminUser.query.count()
            if admin_count == 0:
                print("\n⚠ No admin user found. Create one with:")
                print("  python -m flask create-admin")
            else:
                print(f"\n✓ Found {admin_count} admin user(s)")
            
            # Check if users exist
            user_count = User.query.count()
            print(f"✓ Found {user_count} regular user(s)")
            
            # Check if requests exist
            request_count = Request.query.count()
            print(f"✓ Found {request_count} request(s)")
            
            print("\n✅ Database initialization complete!")
            print("\nNext steps:")
            print("1. If no admin exists: python -m flask create-admin")
            print("2. Reload your web app in PythonAnywhere Web tab")
            print("3. Visit your site!")
            
        except Exception as e:
            print(f"\n❌ Error creating tables: {e}")
            print("\nTroubleshooting:")
            print("1. Check your DATABASE_URL in .env")
            print("2. For MySQL: Ensure database exists and credentials are correct")
            print("3. For SQLite: Ensure directory has write permissions")
            return False
    
    return True

if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)