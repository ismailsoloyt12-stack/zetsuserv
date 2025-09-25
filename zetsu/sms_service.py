"""
FREE OTP Service using pyotp
No external services or costs required
"""

import pyotp
import random
import string
from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Mail, Message
import os

class OTPService:
    def __init__(self):
        """Initialize FREE OTP service."""
        # Use a secret key for OTP generation (stored in environment or generated)
        self.secret_key = os.getenv('OTP_SECRET_KEY', pyotp.random_base32())
        
        # Determine mode based on email configuration
        self.mail_configured = bool(os.getenv('MAIL_USERNAME') and os.getenv('MAIL_PASSWORD'))
        
        if self.mail_configured:
            self.mode = 'email'
            print("✅ OTP Service: Email mode (codes sent to email)")
        else:
            self.mode = 'console'
            print("📝 OTP Service: Console mode (codes shown in terminal)")
        
        # Store OTPs in memory (in production, use Redis or database)
        self.otp_storage = {}
    
    def generate_otp(self, identifier):
        """Generate a 6-digit OTP using pyotp."""
        # Create a TOTP instance with 10 minute validity
        totp = pyotp.TOTP(self.secret_key, interval=600)  # 600 seconds = 10 minutes
        
        # Generate current OTP
        otp = totp.now()
        
        # Ensure it's 6 digits
        if len(otp) < 6:
            otp = otp.zfill(6)
        
        # Store OTP with metadata
        self.otp_storage[identifier] = {
            'code': otp,
            'created_at': datetime.now(),
            'attempts': 0,
            'expires_at': datetime.now() + timedelta(minutes=10)
        }
        
        return otp
    
    def verify_otp(self, identifier, code):
        """Verify an OTP code."""
        if identifier not in self.otp_storage:
            return {
                'success': False,
                'error': 'No OTP found for this identifier'
            }
        
        otp_data = self.otp_storage[identifier]
        
        # Check expiration
        if datetime.now() > otp_data['expires_at']:
            del self.otp_storage[identifier]
            return {
                'success': False,
                'error': 'OTP has expired. Please request a new one'
            }
        
        # Check attempts
        if otp_data['attempts'] >= 3:
            del self.otp_storage[identifier]
            return {
                'success': False,
                'error': 'Too many failed attempts. Please request a new OTP'
            }
        
        # Verify code
        if str(code) == str(otp_data['code']):
            del self.otp_storage[identifier]  # Remove after successful verification
            return {
                'success': True,
                'message': 'OTP verified successfully'
            }
        else:
            otp_data['attempts'] += 1
            remaining = 3 - otp_data['attempts']
            return {
                'success': False,
                'error': f'Invalid OTP. {remaining} attempts remaining'
            }
    
    def send_otp(self, identifier, contact_info):
        """Send OTP via email or display in console."""
        otp = self.generate_otp(identifier)
        
        # Try to find email address for the user
        email_to_use = None
        
        # Check if contact_info is an email
        if '@' in contact_info:
            email_to_use = contact_info
        else:
            # If it's a phone number, try to get email from session or current user
            from flask import session
            from flask_login import current_user
            
            # First check if user is logged in
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                if hasattr(current_user, 'email'):
                    email_to_use = current_user.email
            
            # Check session for stored email
            if not email_to_use:
                email_to_use = session.get('user_email')
        
        # If we have email configuration and an email address, send to email
        if self.mail_configured and email_to_use:
            result = self._send_email_otp(email_to_use, otp)
            # Also show in console for admin monitoring
            self._display_console_otp(contact_info, otp)
            return result
        else:
            # Fallback to console only
            return self._display_console_otp(contact_info, otp)
    
    def _send_email_otp(self, email, otp):
        """Send OTP via email."""
        try:
            from flask import current_app
            from flask_mail import Mail, Message
            
            mail = Mail(current_app)
            
            msg = Message(
                'Your ZetsuServ Verification Code',
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@zetsuserv.com'),
                recipients=[email]
            )
            
            msg.body = f'''
============================================================
🔐 FREE OTP VERIFICATION
Your verification code is: {otp}
Valid for: 10 minutes
============================================================

If you didn't request this code, please ignore this email.
'''
            
            msg.html = f'''
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 28px;">🔐 ZetsuServ Verification</h1>
    </div>
    
    <!-- Console-style OTP display -->
    <div style="background: #1e1e1e; color: #00ff00; padding: 30px; font-family: 'Courier New', monospace; border: 2px solid #333;">
        <div style="text-align: center; line-height: 1.6;">
            <div style="color: #00ff00; margin-bottom: 10px;">============================================================</div>
            <div style="color: #00ffff; font-size: 18px; margin: 10px 0;">🔐 FREE OTP VERIFICATION (No SMS costs!)</div>
            <div style="color: #ffffff; margin: 10px 0;">Contact: {email if '@' in email else 'User'}</div>
            <div style="background: #2d2d2d; border: 2px solid #00ff00; padding: 15px; margin: 20px auto; display: inline-block; border-radius: 5px;">
                <div style="color: #ffff00; font-size: 14px; margin-bottom: 5px;">CODE:</div>
                <div style="color: #00ff00; font-size: 36px; font-weight: bold; letter-spacing: 8px;">{otp}</div>
            </div>
            <div style="color: #ff6b6b; margin: 10px 0;">Valid for: 10 minutes</div>
            <div style="color: #00ff00; margin-top: 10px;">============================================================</div>
        </div>
    </div>
    
    <!-- Instructions -->
    <div style="background: #f8f9fa; padding: 25px; border-radius: 0 0 10px 10px;">
        <h3 style="color: #333; margin-top: 0;">👉 How to use this code:</h3>
        <ol style="color: #666; line-height: 1.8;">
            <li>Go back to the ZetsuServ chatbot</li>
            <li>Enter this 6-digit code in the verification field</li>
            <li>Click "Verify Code" to complete your order</li>
        </ol>
        
        <div style="background: #e8f4fd; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0;">
            <p style="color: #1976D2; margin: 0; font-weight: bold;">ℹ️ Important:</p>
            <p style="color: #666; margin: 5px 0 0 0;">This code will expire in 10 minutes. If it expires, you can request a new one.</p>
        </div>
        
        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
        
        <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
            🔒 This is an automated security email from ZetsuServ. If you didn't request this code, please ignore this email.
        </p>
    </div>
</div>
'''
            
            mail.send(msg)
            
            current_app.logger.info(f"OTP sent to {email}")
            
            # Also log to console for debugging
            print(f"\n📧 OTP sent to: {email}")
            
            return {
                'success': True,
                'message': 'Verification code sent to your email',
                'mode': 'email'
            }
            
        except Exception as e:
            current_app.logger.error(f"Email OTP failed: {str(e)}")
            # Fallback to console
            return self._display_console_otp(email, otp)
    
    def _display_console_otp(self, contact_info, otp):
        """Display OTP in console (FREE demo mode)."""
        current_app.logger.info(f"CONSOLE MODE - OTP for {contact_info}: {otp}")
        
        # Display prominently in console
        print(f"\n" + "="*60)
        print(f"🔐 FREE OTP VERIFICATION (No SMS costs!)")
        print(f"Contact: {contact_info}")
        print(f"CODE: {otp}")
        print(f"Valid for: 10 minutes")
        print("="*60 + "\n")
        
        return {
            'success': True,
            'message': 'Verification code displayed in console',
            'demo_code': otp,  # Include for testing
            'mode': 'console'
        }
    
    def cleanup_expired(self):
        """Remove expired OTPs from storage."""
        now = datetime.now()
        expired_keys = [
            key for key, data in self.otp_storage.items()
            if now > data['expires_at']
        ]
        for key in expired_keys:
            del self.otp_storage[key]

# Global OTP service instance
otp_service = OTPService()

# Compatibility functions for existing code
def send_verification_sms(phone_number, code):
    """Compatibility wrapper - now sends OTP instead of SMS."""
    return otp_service.send_otp(phone_number, phone_number)

def is_production_mode():
    """Check if OTP service is in production mode."""
    return otp_service.mode == 'email'

# Export the service
sms_service = otp_service  # For backward compatibility
