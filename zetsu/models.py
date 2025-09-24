from datetime import datetime
from flask_login import UserMixin
import json
# Import db from parent module to use single instance
from . import db

class Request(db.Model):
    """Client request model."""
    __tablename__ = 'requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Link to user account
    client_name = db.Column(db.String(100), nullable=False)
    client_email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    project_title = db.Column(db.String(200), nullable=False)
    project_type = db.Column(db.String(50), nullable=False)  # landing, business, ecommerce
    pages_required = db.Column(db.Integer, nullable=False)
    budget = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    uploaded_files = db.Column(db.Text)  # JSON array of file paths
    status = db.Column(db.String(20), default='new')  # new, in_progress, delivered, closed
    tracking_code = db.Column(db.String(20), unique=True)  # Store tracking code
    tracking_password = db.Column(db.String(200))  # Encrypted password for secure tracking
    # Queue management fields
    queue_position = db.Column(db.Integer, nullable=True)  # Position in queue (null = activated)
    queue_activated_at = db.Column(db.DateTime, nullable=True)  # When order was activated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Request {self.project_title} by {self.client_name}>'
    
    def get_uploaded_files(self):
        """Return uploaded files as list."""
        if self.uploaded_files:
            return json.loads(self.uploaded_files)
        return []
    
    def set_uploaded_files(self, files_list):
        """Set uploaded files from list."""
        self.uploaded_files = json.dumps(files_list)
    
    def get_status_badge_class(self):
        """Return CSS class for status badge."""
        status_classes = {
            'new': 'badge-new',
            'in_progress': 'badge-progress',
            'delivered': 'badge-delivered',
            'closed': 'badge-closed'
        }
        return status_classes.get(self.status, 'badge-default')
    
    def get_status_display(self):
        """Return human-readable status."""
        status_display = {
            'new': 'New',
            'in_progress': 'In Progress',
            'delivered': 'Delivered',
            'closed': 'Closed'
        }
        return status_display.get(self.status, 'Unknown')
    
    def get_project_type_display(self):
        """Return human-readable project type."""
        type_display = {
            'landing': 'Landing Page',
            'business': 'Business Website',
            'ecommerce': 'E-commerce'
        }
        return type_display.get(self.project_type, 'Other')
    
    def is_queue_active(self):
        """Check if request is active (not in queue)."""
        return self.queue_position is None or self.queue_position == 0
    
    def get_queue_position(self):
        """Get current queue position."""
        if self.is_queue_active():
            return 0
        # Recalculate actual position based on other waiting requests
        waiting_before = Request.query.filter(
            Request.queue_position.isnot(None),
            Request.queue_position > 0,
            Request.queue_position < self.queue_position
        ).count()
        return waiting_before + 1

class AdminUser(db.Model, UserMixin):
    """Admin user model for authentication."""
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()

class Message(db.Model):
    """Message model for admin-client communication."""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'admin' or 'client'
    sender_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    request = db.relationship('Request', backref=db.backref('messages', lazy='dynamic', order_by='Message.created_at'))
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender_name}>'

class Notification(db.Model):
    """Notification model for important updates."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'status_update', 'message', 'milestone'
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), default='info')  # 'success', 'warning', 'info', 'error'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    request = db.relationship('Request', backref=db.backref('notifications', lazy='dynamic', order_by='Notification.created_at.desc()'))
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'

class OrderProgress(db.Model):
    """Track detailed order progress with steps."""
    __tablename__ = 'order_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    step_name = db.Column(db.String(100), nullable=False)
    step_description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'completed'
    progress_percentage = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Relationship
    request = db.relationship('Request', backref=db.backref('progress_steps', lazy='dynamic', order_by='OrderProgress.step_number'))
    
    def __repr__(self):
        return f'<OrderProgress {self.step_name} - {self.status}>'
    
    def mark_in_progress(self):
        """Mark step as in progress."""
        self.status = 'in_progress'
        self.started_at = datetime.utcnow()
        db.session.commit()
    
    def mark_completed(self):
        """Mark step as completed."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100
        db.session.commit()

class User(db.Model, UserMixin):
    """Customer user model."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))  # URL or path to user's avatar image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    # Email verification fields
    email_verification_code_hash = db.Column(db.String(200))
    email_verification_expires_at = db.Column(db.DateTime)
    last_verification_sent_at = db.Column(db.DateTime)
    # User preferences
    enable_profile_video = db.Column(db.Boolean, default=True)  # Toggle for video background
    video_overlay_strength = db.Column(db.Integer, default=60)  # 0-100 overlay opacity
    
    # Relationship with requests
    requests = db.relationship('Request', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def get_active_orders(self):
        """Get all active orders for this user."""
        return self.requests.filter(Request.status.in_(['new', 'in_progress'])).all()
    
    def get_completed_orders(self):
        """Get all completed orders for this user."""
        return self.requests.filter(Request.status.in_(['delivered', 'closed'])).all()
