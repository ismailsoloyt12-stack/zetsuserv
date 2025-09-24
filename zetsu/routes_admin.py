from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from zetsu.models import db, AdminUser, Request, Message, Notification, OrderProgress, User
from zetsu.forms import LoginForm, StatusUpdateForm
import bcrypt
from datetime import datetime
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to ensure only admin users can access certain routes."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not isinstance(current_user, AdminUser):
            flash('You need admin privileges to access this page.', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Find user by username
        user = AdminUser.query.filter_by(username=form.username.data).first()
        
        if user:
            # Check password
            if bcrypt.checkpw(form.password.data.encode('utf-8'), 
                            user.password_hash.encode('utf-8')):
                # Login successful
                login_user(user)
                user.update_last_login()
                
                flash('Login successful!', 'success')
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
            else:
                flash('Invalid username or password.', 'error')
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('admin/login.html', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    """Admin logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard showing all requests."""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'newest')
    
    # Build query
    query = Request.query
    
    # Apply status filter
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Apply sorting
    if sort_by == 'newest':
        query = query.order_by(Request.created_at.desc())
    elif sort_by == 'oldest':
        query = query.order_by(Request.created_at.asc())
    elif sort_by == 'status':
        query = query.order_by(Request.status, Request.created_at.desc())
    
    # Get all requests
    requests = query.all()
    
    # Get statistics
    stats = {
        'total': Request.query.count(),
        'new': Request.query.filter_by(status='new').count(),
        'in_progress': Request.query.filter_by(status='in_progress').count(),
        'delivered': Request.query.filter_by(status='delivered').count(),
        'closed': Request.query.filter_by(status='closed').count()
    }
    
    return render_template('admin/dashboard.html', 
                         requests=requests,
                         stats=stats,
                         status_filter=status_filter,
                         sort_by=sort_by)

@admin_bp.route('/request/<int:id>')
@admin_required
def view_request(id):
    """View detailed request information."""
    request_obj = Request.query.get_or_404(id)
    status_form = StatusUpdateForm(status=request_obj.status)
    
    # Get messages
    messages = request_obj.messages.all()
    
    # Get progress steps
    progress_steps = request_obj.progress_steps.all()
    if not progress_steps:
        from zetsu.routes_public import create_default_progress_steps
        create_default_progress_steps(request_obj)
        progress_steps = request_obj.progress_steps.all()
    
    # Get tracking code
    from zetsu.routes_public import generate_order_code, generate_tracking_password
    tracking_code = generate_order_code(request_obj)
    
    # Check if order has password, generate if missing
    has_password = bool(request_obj.tracking_password)
    if not has_password:
        # Generate password for existing orders
        tracking_password = generate_tracking_password()
        request_obj.tracking_password = bcrypt.hashpw(
            tracking_password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        db.session.commit()
        flash(f'Generated access key for this order: {tracking_password}', 'info')
    
    return render_template('admin/view_request_improved.html', 
                         request=request_obj,
                         form=status_form,
                         messages=messages,
                         progress_steps=progress_steps,
                         tracking_code=tracking_code,
                         has_password=has_password)

@admin_bp.route('/request/<int:id>/set_status', methods=['POST'])
@admin_required
def set_status(id):
    """Update request status."""
    request_obj = Request.query.get_or_404(id)
    form = StatusUpdateForm()
    
    if form.validate_on_submit():
        old_status = request_obj.get_status_display()
        request_obj.status = form.status.data
        
        # If marking as delivered or closed, activate next in queue
        if form.status.data in ['delivered', 'closed']:
            activate_next_in_queue()
        
        db.session.commit()
        
        new_status = request_obj.get_status_display()
        flash(f'Request status updated from {old_status} to {new_status}.', 'success')
    else:
        flash('Failed to update status. Please try again.', 'error')
    
    return redirect(url_for('admin.view_request', id=id))

@admin_bp.route('/request/<int:id>/regenerate_password', methods=['POST'])
@admin_required
def regenerate_password(id):
    """Regenerate and send access key for an order."""
    request_obj = Request.query.get_or_404(id)
    
    try:
        from zetsu.routes_public import generate_order_code, generate_tracking_password, send_tracking_code_email
        
        # Generate new password
        tracking_password = generate_tracking_password()
        request_obj.tracking_password = bcrypt.hashpw(
            tracking_password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        db.session.commit()
        
        # Send email with new password
        tracking_code = request_obj.tracking_code or generate_order_code(request_obj)
        send_tracking_code_email(request_obj, tracking_code, tracking_password)
        
        flash(f'New access key generated and sent to client: {tracking_password}', 'success')
    except Exception as e:
        flash(f'Failed to regenerate password: {e}', 'error')
    
    return redirect(url_for('admin.view_request', id=id))

@admin_bp.route('/request/<int:id>/delete', methods=['POST'])
@admin_required
def delete_request(id):
    """Delete a request with all related data."""
    request_obj = Request.query.get_or_404(id)
    
    try:
        # Delete related messages first
        Message.query.filter_by(request_id=id).delete()
        
        # Delete related notifications
        Notification.query.filter_by(request_id=id).delete()
        
        # Delete related progress steps
        OrderProgress.query.filter_by(request_id=id).delete()
        
        # Delete uploaded files
        import os
        for file_path in request_obj.get_uploaded_files():
            full_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 
                                   os.path.basename(file_path))
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass  # Continue even if file deletion fails
        
        # Finally delete the request
        db.session.delete(request_obj)
        db.session.commit()
        
        flash(f'Request "{request_obj.project_title}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting request: {e}')
        flash(f'Error deleting request: {str(e)}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/request/<int:id>/send_message', methods=['POST'])
@admin_required
def send_admin_message(id):
    """Send message from admin to client."""
    request_obj = Request.query.get_or_404(id)
    message_content = request.form.get('message', '').strip()
    
    if not message_content:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
    
    # Create message
    message = Message(
        request_id=id,
        sender_type='admin',
        sender_name=current_user.username,
        content=message_content
    )
    db.session.add(message)
    
    # Create notification for client
    notification = Notification(
        request_id=id,
        type='message',
        title='New Message from Admin',
        content=f'{current_user.username}: {message_content[:100]}...',
        icon='info'
    )
    db.session.add(notification)
    
    db.session.commit()
    
    # Send email notification to client
    try:
        send_client_notification_email(request_obj, message_content)
    except Exception as e:
        current_app.logger.warning(f'Failed to send client notification email: {e}')
    
    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'content': message.content,
            'sender_type': message.sender_type,
            'sender_name': message.sender_name,
            'created_at': message.created_at.isoformat()
        }
    })

@admin_bp.route('/request/<int:id>/update_progress', methods=['POST'])
@admin_required
def update_progress(id):
    """Update order progress step."""
    request_obj = Request.query.get_or_404(id)
    step_id = request.form.get('step_id', type=int)
    action = request.form.get('action')  # 'start', 'complete', 'update', 'reset'
    notes = request.form.get('notes', '')
    progress = request.form.get('progress', 0, type=int)
    
    if not step_id:
        return jsonify({'success': False, 'error': 'Step ID required'}), 400
    
    step = OrderProgress.query.filter_by(id=step_id, request_id=id).first_or_404()
    
    if action == 'start':
        # Start the progress step
        step.status = 'in_progress'
        step.started_at = datetime.utcnow()
        step.progress_percentage = progress if progress > 0 else 10
        if notes:
            step.notes = notes
        
        # Create notification
        notification = Notification(
            request_id=id,
            type='milestone',
            title=f'Progress Update: {step.step_name}',
            content=f'Work has started on: {step.step_name}',
            icon='success'
        )
        db.session.add(notification)
        
    elif action == 'complete':
        # Complete the step
        step.status = 'completed'
        step.completed_at = datetime.utcnow()
        step.progress_percentage = 100
        if notes:
            step.notes = notes
        
        # Auto-start next step if exists
        next_step = OrderProgress.query.filter(
            OrderProgress.request_id == id,
            OrderProgress.step_number > step.step_number,
            OrderProgress.status == 'pending'
        ).order_by(OrderProgress.step_number).first()
        
        if next_step:
            next_step.status = 'in_progress'
            next_step.started_at = datetime.utcnow()
            next_step.progress_percentage = 10
        
        # Create notification
        notification = Notification(
            request_id=id,
            type='milestone',
            title=f'Milestone Completed: {step.step_name}',
            content=f'{step.step_name} has been completed successfully!',
            icon='success'
        )
        db.session.add(notification)
        
    elif action == 'update':
        # Update progress percentage only
        step.progress_percentage = min(max(progress, 0), 100)
        if notes:
            step.notes = notes
            
    elif action == 'reset':
        # Reset step to pending
        step.status = 'pending'
        step.progress_percentage = 0
        step.started_at = None
        step.completed_at = None
        if notes:
            step.notes = notes
    
    db.session.commit()
    
    # Send email notification
    try:
        send_progress_update_email(request_obj, step, action)
    except Exception as e:
        current_app.logger.warning(f'Failed to send progress update email: {e}')
    
    flash(f'Progress updated for: {step.step_name}', 'success')
    return jsonify({'success': True, 'step': {
        'id': step.id,
        'status': step.status,
        'progress': step.progress_percentage
    }})

@admin_bp.route('/users')
@admin_required
def users():
    """Admin - list all customer users with management actions."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Admin - delete a user account and detach related data."""
    user = User.query.get_or_404(user_id)

    # Safety: prevent deleting admin accounts through this route
    if isinstance(user, AdminUser):
        flash('Cannot delete admin accounts from this page.', 'error')
        return redirect(url_for('admin.users'))

    try:
        # Detach any requests linked to this user
        for req in user.requests.all():
            req.user_id = None
        db.session.flush()

        # Remove user's avatar file if stored locally
        if user.avatar_url and user.avatar_url.startswith('/static/uploads/avatars/'):
            import os
            avatar_filename = user.avatar_url.split('/static/uploads/avatars/')[-1]
            avatar_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars', avatar_filename)
            try:
                if os.path.exists(avatar_path):
                    os.remove(avatar_path)
            except Exception as e:
                current_app.logger.warning(f'Failed to remove avatar file: {e}')

        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        flash('User account has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting user: {e}')
        flash('An error occurred while deleting the user.', 'error')

    return redirect(url_for('admin.users'))

@admin_bp.route('/request/<int:id>/activate', methods=['POST'])
@admin_required
def activate_request(id):
    """Manually activate a request from queue."""
    request_obj = Request.query.get_or_404(id)
    
    if request_obj.queue_position and request_obj.queue_position > 0:
        # Remove from queue
        old_position = request_obj.queue_position
        request_obj.queue_position = None
        request_obj.queue_activated_at = datetime.now()
        request_obj.status = 'in_progress'
        
        # Update positions of others in queue
        Request.query.filter(
            Request.queue_position > old_position
        ).update({Request.queue_position: Request.queue_position - 1})
        
        db.session.commit()
        
        # Send activation email
        try:
            from zetsu.routes_public import generate_order_code, send_queue_activation_email
            tracking_code = request_obj.tracking_code or generate_order_code(request_obj)
            send_queue_activation_email(request_obj, tracking_code)
        except Exception as e:
            current_app.logger.warning(f'Failed to send activation email: {e}')
        
        flash(f'Request "{request_obj.project_title}" has been activated!', 'success')
    else:
        flash('This request is already active.', 'info')
    
    return redirect(url_for('admin.view_request', id=id))

@admin_bp.route('/queue')
@admin_required
def queue_management():
    """Queue management page for admin."""
    # Get all requests in queue
    queued = Request.query.filter(
        Request.queue_position.isnot(None),
        Request.queue_position > 0
    ).order_by(Request.queue_position).all()
    
    # Get active requests
    active = Request.query.filter(
        db.or_(
            Request.queue_position.is_(None),
            Request.queue_position == 0
        ),
        Request.status.in_(['new', 'in_progress'])
    ).order_by(Request.created_at.desc()).all()
    
    return render_template('admin/queue_management.html',
        queued_requests=queued,
        active_requests=active
    )

@admin_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications."""
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = Notification.query.filter_by(is_read=False).count()
    
    # Mark all as read
    Notification.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    
    return render_template('admin/notifications.html', 
                         notifications=notifications,
                         unread_count=unread_count)

def send_client_notification_email(request_obj, message_content):
    """Send email notification to client for new message."""
    try:
        from flask_mail import Message as MailMessage, Mail
        from zetsu.routes_public import generate_order_code
        
        mail = Mail(current_app)
        
        if not current_app.config.get('MAIL_USERNAME'):
            return
        
        tracking_code = generate_order_code(request_obj)
        tracking_url = url_for('public.track_order', order_code=tracking_code, _external=True)
        
        msg = MailMessage(
            subject=f'New Message from ZetsuServ Team',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[request_obj.client_email]
        )
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h2>New Message from Our Team</h2>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hello {request_obj.client_name},</p>
                
                <p>You have a new message regarding your project: <strong>{request_obj.project_title}</strong></p>
                
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <p style="margin: 0; color: #333;">{message_content}</p>
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{tracking_url}" style="display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">View & Reply</a>
                </p>
                
                <p style="color: #666; margin-top: 30px;">Best regards,<br><strong>The ZetsuServ Team</strong></p>
            </div>
        </div>
        """
        
        msg.body = f"""
        Hello {request_obj.client_name},
        
        You have a new message regarding your project: {request_obj.project_title}
        
        Message:
        {message_content}
        
        View and reply at: {tracking_url}
        
        Best regards,
        The ZetsuServ Team
        """
        
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send client notification email: {e}')

def send_progress_update_email(request_obj, step, action):
    """Send email notification for progress updates."""
    try:
        from flask_mail import Message as MailMessage, Mail
        from zetsu.routes_public import generate_order_code
        
        mail = Mail(current_app)
        
        if not current_app.config.get('MAIL_USERNAME'):
            return
        
        tracking_code = generate_order_code(request_obj)
        tracking_url = url_for('public.track_order', order_code=tracking_code, _external=True)
        
        if action == 'complete':
            subject = f'Milestone Completed: {step.step_name}'
            status_msg = f'Great news! We have completed: {step.step_name}'
        elif action == 'start':
            subject = f'Work Started: {step.step_name}'
            status_msg = f'We have started working on: {step.step_name}'
        else:
            return  # Don't send email for simple updates
        
        msg = MailMessage(
            subject=subject,
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[request_obj.client_email]
        )
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #00c851 0%, #00a846 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h2>Project Progress Update</h2>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hello {request_obj.client_name},</p>
                
                <p>{status_msg}</p>
                
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">{step.step_name}</h3>
                    <p style="color: #666;">{step.step_description}</p>
                    {f'<p style="color: #999; font-style: italic;">Note: {step.notes}</p>' if step.notes else ''}
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{tracking_url}" style="display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #00c851 0%, #00a846 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Track Your Project</a>
                </p>
                
                <p style="color: #666; margin-top: 30px;">Best regards,<br><strong>The ZetsuServ Team</strong></p>
            </div>
        </div>
        """
        
        msg.body = f"""
        Hello {request_obj.client_name},
        
        {status_msg}
        
        {step.step_name}
        {step.step_description}
        {f'Note: {step.notes}' if step.notes else ''}
        
        Track your project at: {tracking_url}
        
        Best regards,
        The ZetsuServ Team
        """
        
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send progress update email: {e}')

# Error handlers for admin section
@admin_bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors in admin section."""
    return render_template('admin/404.html'), 404

@admin_bp.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors in admin section."""
    flash('You do not have permission to access this resource.', 'error')
    return redirect(url_for('admin.dashboard'))

def activate_next_in_queue():
    """Activate the next request in queue."""
    # Find the request with lowest queue position
    next_request = Request.query.filter(
        Request.queue_position.isnot(None),
        Request.queue_position > 0
    ).order_by(Request.queue_position).first()
    
    if next_request:
        # Activate it
        old_position = next_request.queue_position
        next_request.queue_position = None
        next_request.queue_activated_at = datetime.now()
        next_request.status = 'in_progress'
        
        # Update positions of others
        Request.query.filter(
            Request.queue_position > old_position
        ).update({Request.queue_position: Request.queue_position - 1})
        
        db.session.commit()
        
        # Send activation email with password
        try:
            from zetsu.routes_public import generate_order_code, send_queue_activation_email, generate_tracking_password
            tracking_code = next_request.tracking_code or generate_order_code(next_request)
            
            # Check if password exists, if not generate one
            if not next_request.tracking_password:
                tracking_password = generate_tracking_password()
                next_request.tracking_password = bcrypt.hashpw(
                    tracking_password.encode('utf-8'), 
                    bcrypt.gensalt()
                ).decode('utf-8')
                db.session.commit()
            else:
                # For existing orders, generate a new readable password
                tracking_password = generate_tracking_password()
                next_request.tracking_password = bcrypt.hashpw(
                    tracking_password.encode('utf-8'), 
                    bcrypt.gensalt()
                ).decode('utf-8')
                db.session.commit()
            
            send_queue_activation_email(next_request, tracking_code, tracking_password)
        except Exception as e:
            current_app.logger.warning(f'Failed to send queue activation email: {e}')
        
        return next_request
    return None
