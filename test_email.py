#!/usr/bin/env python
"""Test email configuration and sending."""

from zetsu import create_app
from flask_mail import Mail, Message
import os

def test_email_config():
    """Test if email is configured correctly."""
    app = create_app()
    
    with app.app_context():
        print("\n📧 Testing Email Configuration")
        print("=" * 50)
        
        # Check configuration
        print("\n✅ Configuration Check:")
        print(f"  MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
        print(f"  MAIL_PORT: {app.config.get('MAIL_PORT')}")
        print(f"  MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"  MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
        print(f"  MAIL_PASSWORD: {'***' if app.config.get('MAIL_PASSWORD') else 'NOT SET'}")
        print(f"  MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
        print(f"  ADMIN_EMAIL: {app.config.get('ADMIN_EMAIL')}")
        
        # Test if Mail extension is initialized
        try:
            mail = Mail(app)
            print("\n✅ Flask-Mail initialized successfully!")
        except Exception as e:
            print(f"\n❌ Flask-Mail initialization failed: {e}")
            return False
        
        # Test sending a simple email
        print("\n📨 Testing Email Send (dry run)...")
        try:
            # Create a test message
            msg = Message(
                subject='ZetsuServ Test Email',
                sender=app.config.get('MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME'),
                recipients=['test@example.com']  # Use a test address
            )
            msg.body = "This is a test email from ZetsuServ."
            msg.html = "<p>This is a <b>test email</b> from ZetsuServ.</p>"
            
            # Don't actually send in test, just verify message creation
            print("  ✅ Test message created successfully")
            print(f"  From: {msg.sender}")
            print(f"  To: {msg.recipients}")
            print(f"  Subject: {msg.subject}")
            
            # Check if we can connect to mail server
            with mail.connect() as conn:
                print("  ✅ Successfully connected to mail server!")
                
        except Exception as e:
            print(f"  ❌ Email test failed: {e}")
            print("\n  Possible issues:")
            print("  1. Check your Gmail App Password (not regular password)")
            print("  2. Enable 2-factor authentication in Gmail")
            print("  3. Generate App Password: Google Account > Security > App passwords")
            print("  4. Update MAIL_PASSWORD in .env file")
            return False
        
        print("\n" + "=" * 50)
        print("✅ Email configuration appears to be working!")
        print("=" * 50 + "\n")
        
        return True

if __name__ == "__main__":
    test_email_config()