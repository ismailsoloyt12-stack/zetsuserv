from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, FileField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo
from flask_wtf.file import FileAllowed

class RequestForm(FlaskForm):
    """Form for client service requests."""
    client_name = StringField('Full Name', validators=[
        DataRequired(message='Name is required'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    
    client_email = StringField('Email Address', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    
    phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required'),
        Length(min=10, max=20, message='Please enter a valid phone number')
    ])
    
    project_title = StringField('Project Title', validators=[
        DataRequired(message='Project title is required'),
        Length(min=3, max=200, message='Title must be between 3 and 200 characters')
    ])
    
    project_type = SelectField('Project Type', validators=[
        DataRequired(message='Please select a project type')
    ], choices=[
        ('', 'Select Project Type'),
        ('landing', 'Landing Page Website'),
        ('business', 'Business Website'),
        ('ecommerce', 'E-commerce Platform')
    ])
    
    pages_required = IntegerField('Number of Pages Required', validators=[
        DataRequired(message='Number of pages is required'),
        NumberRange(min=1, max=100, message='Please enter a number between 1 and 100')
    ])
    
    budget = SelectField('Budget Range', validators=[
        DataRequired(message='Please select your budget range')
    ], choices=[
        ('', 'Select Budget Range'),
        ('$500-$1000', '$500 - $1,000'),
        ('$1000-$5000', '$1,000 - $5,000'),
        ('$5000-$10000', '$5,000 - $10,000'),
        ('$10000-$25000', '$10,000 - $25,000'),
        ('$25000+', '$25,000+')
    ])
    
    details = TextAreaField('Project Details', validators=[
        DataRequired(message='Project details are required'),
        Length(min=20, max=5000, message='Details must be between 20 and 5000 characters')
    ])
    
    files = FileField('Upload Files (Optional)', validators=[
        Optional(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'pdf', 'zip', 'doc', 'docx'], 
                   'Only PNG, JPG, GIF, PDF, ZIP, DOC, DOCX files are allowed')
    ])
    
    submit = SubmitField('Submit Request')

class LoginForm(FlaskForm):
    """Form for admin login."""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required'),
        Length(min=3, max=80)
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    
    submit = SubmitField('Login')

class StatusUpdateForm(FlaskForm):
    """Form for updating request status."""
    status = SelectField('Status', 
                        choices=[('new', 'New'),
                                ('in_progress', 'In Progress'),
                                ('delivered', 'Delivered'),
                                ('closed', 'Closed')])
    submit = SubmitField('Update Status')

class UserRegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    full_name = StringField('Full Name', validators=[Length(max=100)])
    phone = StringField('Phone', validators=[Length(max=20)])
    company = StringField('Company', validators=[Length(max=100)])
    agree_terms = BooleanField('I agree to the Terms of Service', validators=[DataRequired()])
    submit = SubmitField('Create Account')

class UserLoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class TrackOrderForm(FlaskForm):
    """Track order form."""
    tracking_code = StringField('Tracking Code', validators=[
        DataRequired(),
        Length(min=6, max=20)
    ])
    submit = SubmitField('Track Order')
