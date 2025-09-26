"""
Flask CLI commands for administrative tasks.
This module provides command-line interface commands for database and admin management.
"""

import click
from flask import Blueprint
from flask.cli import with_appcontext
from zetsu import db
from zetsu.models import AdminUser, User, Request
import bcrypt
from datetime import datetime
import sys

bp = Blueprint('commands', __name__, cli_group=None)

@bp.cli.command('create-admin')
@with_appcontext
def create_admin_command():
    """Create an administrative user interactively."""
    print("\n" + "="*50)
    print("CREATE ADMIN USER")
    print("="*50 + "\n")
    
    # Get username
    username = click.prompt('Enter admin username', default='admin', type=str)
    
    # Check if username already exists
    existing_admin = AdminUser.query.filter_by(username=username).first()
    if existing_admin:
        click.echo(click.style(f'\n❌ Error: Admin user "{username}" already exists!', fg='red'))
        if click.confirm('Do you want to create a different admin?'):
            return create_admin_command()
        return
    
    # Get email
    email = click.prompt('Enter admin email', default=f'{username}@zetsuserv.com', type=str)
    
    # Check if email already exists
    existing_email = AdminUser.query.filter_by(email=email).first()
    if existing_email:
        click.echo(click.style(f'\n❌ Error: Email "{email}" is already in use!', fg='red'))
        return
    
    # Get password (hidden input)
    password = click.prompt('Enter admin password', hide_input=True, confirmation_prompt=True)
    
    if len(password) < 8:
        click.echo(click.style('\n❌ Error: Password must be at least 8 characters long!', fg='red'))
        return
    
    # Create admin user
    try:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        admin = AdminUser(
            username=username,
            email=email,
            password_hash=password_hash.decode('utf-8'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(admin)
        db.session.commit()
        
        click.echo(click.style(f'\n✅ Admin user "{username}" created successfully!', fg='green'))
        click.echo(f'   Email: {email}')
        click.echo(f'   Login URL: /admin/login')
        
    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f'\n❌ Error creating admin: {str(e)}', fg='red'))
        sys.exit(1)

@bp.cli.command('list-admins')
@with_appcontext
def list_admins_command():
    """List all administrative users."""
    admins = AdminUser.query.all()
    
    if not admins:
        click.echo(click.style('\nNo admin users found. Create one with: flask create-admin', fg='yellow'))
        return
    
    click.echo('\n' + '='*60)
    click.echo('ADMIN USERS')
    click.echo('='*60)
    
    for admin in admins:
        click.echo(f'\nID: {admin.id}')
        click.echo(f'Username: {admin.username}')
        click.echo(f'Email: {admin.email}')
        click.echo(f'Created: {admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if admin.created_at else "Unknown"}')
        click.echo('-'*40)

@bp.cli.command('delete-admin')
@with_appcontext
def delete_admin_command():
    """Delete an administrative user."""
    username = click.prompt('Enter admin username to delete', type=str)
    
    admin = AdminUser.query.filter_by(username=username).first()
    if not admin:
        click.echo(click.style(f'\n❌ Error: Admin user "{username}" not found!', fg='red'))
        return
    
    if click.confirm(f'Are you sure you want to delete admin "{username}"?'):
        try:
            db.session.delete(admin)
            db.session.commit()
            click.echo(click.style(f'\n✅ Admin user "{username}" deleted successfully!', fg='green'))
        except Exception as e:
            db.session.rollback()
            click.echo(click.style(f'\n❌ Error deleting admin: {str(e)}', fg='red'))

@bp.cli.command('reset-admin-password')
@with_appcontext
def reset_admin_password_command():
    """Reset an admin user's password."""
    username = click.prompt('Enter admin username', type=str)
    
    admin = AdminUser.query.filter_by(username=username).first()
    if not admin:
        click.echo(click.style(f'\n❌ Error: Admin user "{username}" not found!', fg='red'))
        return
    
    # Get new password
    password = click.prompt('Enter new password', hide_input=True, confirmation_prompt=True)
    
    if len(password) < 8:
        click.echo(click.style('\n❌ Error: Password must be at least 8 characters long!', fg='red'))
        return
    
    try:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        admin.password_hash = password_hash.decode('utf-8')
        db.session.commit()
        click.echo(click.style(f'\n✅ Password reset successfully for admin "{username}"!', fg='green'))
    except Exception as e:
        db.session.rollback()
        click.echo(click.style(f'\n❌ Error resetting password: {str(e)}', fg='red'))

@bp.cli.command('init-db')
@with_appcontext
def init_database_command():
    """Initialize the database with all tables."""
    try:
        db.create_all()
        click.echo(click.style('\n✅ Database initialized successfully!', fg='green'))
        
        # Check table count
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        click.echo(f'   Created {len(tables)} tables: {", ".join(sorted(tables))}')
        
    except Exception as e:
        click.echo(click.style(f'\n❌ Error initializing database: {str(e)}', fg='red'))
        sys.exit(1)

@bp.cli.command('drop-db')
@with_appcontext
def drop_database_command():
    """Drop all database tables (DANGEROUS!)."""
    click.echo(click.style('\n⚠️  WARNING: This will delete ALL data!', fg='yellow'))
    
    if click.confirm('Are you absolutely sure you want to drop all tables?'):
        confirm_text = click.prompt('Type "DELETE ALL" to confirm', type=str)
        if confirm_text == "DELETE ALL":
            try:
                db.drop_all()
                click.echo(click.style('\n✅ All tables dropped successfully!', fg='green'))
            except Exception as e:
                click.echo(click.style(f'\n❌ Error dropping tables: {str(e)}', fg='red'))
        else:
            click.echo('\nOperation cancelled.')

@bp.cli.command('db-status')
@with_appcontext
def database_status_command():
    """Show database status and statistics."""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        click.echo('\n' + '='*60)
        click.echo('DATABASE STATUS')
        click.echo('='*60)
        
        # Database URL (hide password)
        db_url = str(db.engine.url)
        if '@' in db_url:
            parts = db_url.split('@')
            if len(parts) > 1:
                db_url = parts[0].split('://')[0] + '://[HIDDEN]@' + parts[1]
        
        click.echo(f'\nDatabase URL: {db_url}')
        click.echo(f'Tables: {len(tables)}')
        
        if tables:
            click.echo('\nTable Statistics:')
            click.echo('-'*40)
            
            # Count records in each table
            admin_count = AdminUser.query.count()
            user_count = User.query.count()
            request_count = Request.query.count()
            
            click.echo(f'  admin_users: {admin_count} records')
            click.echo(f'  users: {user_count} records')
            click.echo(f'  requests: {request_count} records')
            
            click.echo('\nAll Tables:')
            for table in sorted(tables):
                click.echo(f'  - {table}')
        else:
            click.echo(click.style('\n⚠️  No tables found! Run "flask init-db" to create them.', fg='yellow'))
            
    except Exception as e:
        click.echo(click.style(f'\n❌ Error checking database status: {str(e)}', fg='red'))