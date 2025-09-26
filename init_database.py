#!/usr/bin/env python
"""
Database Initialization Script for ZetsuServ
This script initializes the database with all required tables.
Run this after configuring your .env file on a new server.
"""

import os
import sys
from pathlib import Path

# Ensure we're in the correct directory
project_home = Path(__file__).resolve().parent
os.chdir(project_home)
sys.path.insert(0, str(project_home))

print("="*60)
print("ZETSUSERV DATABASE INITIALIZATION")
print("="*60)
print()

# Step 1: Load environment variables
print("Step 1: Loading environment variables...")
from dotenv import load_dotenv

env_path = project_home / '.env'
if not env_path.exists():
    print(f"❌ ERROR: No .env file found at {env_path}")
    print("\nPlease create a .env file with your configuration.")
    print("You can copy .env.production as a template:")
    print("  cp .env.production .env")
    print("Then edit .env with your actual values.")
    sys.exit(1)

load_dotenv(env_path)
print(f"✅ Loaded environment from: {env_path}")

# Step 2: Verify critical environment variables
print("\nStep 2: Verifying environment variables...")
required_vars = ['SECRET_KEY', 'DATABASE_URL']
missing_vars = []

for var in required_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("\nPlease set these in your .env file:")
    for var in missing_vars:
        if var == 'SECRET_KEY':
            print(f"  {var}=<generate with: python -c \"import secrets; print(secrets.token_hex(32))\">")
        elif var == 'DATABASE_URL':
            print(f"  {var}=<your database connection string>")
    sys.exit(1)

print("✅ All required environment variables are set")

# Step 3: Set Flask environment
os.environ['FLASK_ENV'] = os.getenv('FLASK_ENV', 'production')
print(f"\nStep 3: Flask environment set to: {os.environ['FLASK_ENV']}")

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