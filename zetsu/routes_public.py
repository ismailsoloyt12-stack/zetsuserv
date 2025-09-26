import os
import secrets
import hashlib
import bcrypt
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from zetsu.models import db, Request, Message, Notification, OrderProgress, User, AdminUser
from zetsu.forms import RequestForm, UserRegistrationForm, UserLoginForm

public_bp = Blueprint('public', __name__)

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file):
    """Save uploaded file and return its path."""
    if file and allowed_file(file.filename):
        # Generate unique filename
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(file.filename)
        filename = random_hex + f_ext
        filename = secure_filename(filename)
        
        # Ensure upload directory exists
        upload_path = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        # Return relative path for storage
        return os.path.join('uploads', filename)
    return None

@public_bp.route('/')
def index():
    """Landing page."""
    return render_template('index.html')

@public_bp.route('/favicon.ico')
def favicon():
    """Serve favicon."""
    import os
    from flask import send_from_directory
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                             'favicon.ico', mimetype='image/vnd.microsoft.icon')

@public_bp.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files."""
    from flask import send_from_directory
    upload_dir = os.path.join(current_app.root_path, '..', 'uploads')
    return send_from_directory(upload_dir, filename)

@public_bp.route('/static/uploads/avatars/<path:filename>')
def serve_avatar(filename):
    """Serve avatar images."""
    from flask import send_from_directory
    avatar_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
    return send_from_directory(avatar_dir, filename)

@public_bp.route('/request', methods=['GET', 'POST'])
def request_service():
    """Service request form."""
    form = RequestForm()
    
    if form.validate_on_submit():
        try:
            # Check if there are any active orders (to determine queue position)
            active_count = Request.query.filter(
                db.or_(
                    Request.queue_position.is_(None),
                    Request.queue_position == 0
                )
            ).count()
            
            # Get highest queue position
            max_queue = db.session.query(db.func.max(Request.queue_position)).scalar() or 0
            
            # Determine queue position
            # IMPORTANT: Only activate if NO active orders exist
            if active_count == 0:
                queue_pos = 1  # First order, will be activated
            else:
                queue_pos = max_queue + 1  # Add to end of queue
            
            # Create new request
            new_request = Request(
                client_name=form.client_name.data,
                client_email=form.client_email.data,
                phone=form.phone.data,
                project_title=form.project_title.data,
                project_type=form.project_type.data,
                pages_required=form.pages_required.data,
                budget=form.budget.data,
                details=form.details.data,
                status='new',
                queue_position=queue_pos
            )
            
            # Handle file uploads
            uploaded_files = []
            if 'files' in current_app.config and form.files.data:
                files = request.files.getlist('files')
                for file in files:
                    if file and file.filename:
                        file_path = save_uploaded_file(file)
                        if file_path:
                            uploaded_files.append(file_path)
            
            # Save uploaded files paths
            if uploaded_files:
                new_request.set_uploaded_files(uploaded_files)
            
            # Link to user if logged in
            if current_user.is_authenticated:
                new_request.user_id = current_user.id
            
            # Save to database
            db.session.add(new_request)
            db.session.commit()
            
            # Generate tracking code and password
            tracking_code = generate_order_code(new_request)
            tracking_password = generate_tracking_password()
            new_request.tracking_code = tracking_code
            new_request.tracking_password = bcrypt.hashpw(tracking_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.session.commit()
            
            # Create initial progress steps
            create_default_progress_steps(new_request)
            
            # Send notification email with password
            try:
                send_notification_email(new_request)
                send_tracking_code_email(new_request, tracking_code, tracking_password)
            except Exception as e:
                current_app.logger.warning(f'Failed to send notification email: {e}')
            
            # Store tracking code in session for thank you page
            from flask import session
            session['tracking_code'] = tracking_code
            session['request_id'] = new_request.id
            
            # Check if order should be activated
            # Only activate if there were NO active orders
            if active_count == 0:
                # Activate immediately - no other active orders
                new_request.queue_position = None
                new_request.queue_activated_at = datetime.now()
                db.session.commit()
                
                # Send activation email with tracking code and password
                try:
                    send_queue_activation_email(new_request, tracking_code, tracking_password)
                except Exception as e:
                    current_app.logger.warning(f'Failed to send activation email: {e}')
                
                # Fix f-string with backslash issue
                message = f"Hey Champ! You're first! Your tracking code is: {tracking_code}"
                flash(message, 'success')
            else:
                flash(f'Your request has been submitted successfully! You are #{ queue_pos - (active_count if active_count > 0 else 0)} in the queue.', 'info')
            
            return redirect(url_for('public.queue_status', request_id=new_request.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error saving request: {e}')
            flash('An error occurred while submitting your request. Please try again.', 'error')
    
    return render_template('request_form.html', form=form)

@public_bp.route('/queue-status/<int:request_id>')
def queue_status(request_id):
    """Display queue status for a request."""
    request_obj = Request.query.get_or_404(request_id)
    
    # Calculate actual queue position
    if request_obj.queue_position is None or request_obj.queue_position == 0:
        queue_position = 0  # Active
    else:
        # Count how many are ahead
        ahead = Request.query.filter(
            Request.queue_position.isnot(None),
            Request.queue_position > 0,
            Request.queue_position < request_obj.queue_position
        ).count()
        queue_position = ahead + 1
    
    # Mask email
    email_parts = request_obj.client_email.split('@')
    if len(email_parts[0]) > 2:
        masked_email = f"{email_parts[0][0]}***{email_parts[0][-1]}@{email_parts[1]}"
    else:
        masked_email = request_obj.client_email
    
    # Get tracking code
    from zetsu.routes_public import generate_order_code
    tracking_code = request_obj.tracking_code or generate_order_code(request_obj)
    
    return render_template('queue_status.html',
        request_id=request_id,
        queue_position=queue_position,
        orders_ahead=queue_position - 1 if queue_position > 0 else 0,
        masked_email=masked_email,
        tracking_code=tracking_code
    )

@public_bp.route('/api/queue-status/<int:request_id>')
def api_queue_status(request_id):
    """API endpoint for queue status."""
    request_obj = Request.query.get_or_404(request_id)
    
    # Calculate actual queue position
    if request_obj.queue_position is None or request_obj.queue_position == 0:
        queue_position = 0  # Active
    else:
        # Count how many are ahead
        ahead = Request.query.filter(
            Request.queue_position.isnot(None),
            Request.queue_position > 0,
            Request.queue_position < request_obj.queue_position
        ).count()
        queue_position = ahead + 1
    
    return jsonify({
        'queue_position': queue_position,
        'is_active': queue_position <= 1,
        'tracking_code': request_obj.tracking_code if queue_position <= 1 else None
    })

@public_bp.route('/thanks')
def thanks():
    """Thank you page after successful submission."""
    return render_template('thanks.html')

@public_bp.route('/track')
def track_order_login():
    """Show secure tracking login page."""
    return render_template('track_login.html')

@public_bp.route('/track/auth', methods=['POST'])
def track_order_auth():
    """Authenticate and redirect to order tracking."""
    order_id = request.form.get('order_id', '').strip()
    password = request.form.get('password', '').strip()
    
    if not order_id or not password:
        flash('Please enter both Order ID and Access Key.', 'error')
        return render_template('track_login.html')
    
    # Extract request ID from order code
    try:
        request_id = int(order_id.split('-')[0])
    except:
        flash('Invalid Order ID format. Please check and try again.', 'error')
        return render_template('track_login.html')
    
    # Get request
    request_obj = Request.query.get(request_id)
    if not request_obj:
        flash('Order not found. Please check your Order ID.', 'error')
        return render_template('track_login.html')
    
    # Verify order code format
    if generate_order_code(request_obj) != order_id:
        flash('Invalid Order ID. Please check and try again.', 'error')
        return render_template('track_login.html')
    
    # CHECK IF ORDER IS STILL IN QUEUE
    if request_obj.queue_position is not None and request_obj.queue_position > 0:
        # Order is in queue - doesn't have tracking access yet
        flash('This order is still in queue. You will receive tracking access when your turn arrives.', 'info')
        return redirect(url_for('public.queue_status', request_id=request_id))
    
    # Verify password
    if not request_obj.tracking_password:
        # For backward compatibility, if no password set, reject
        flash('This order requires password authentication. Please contact support.', 'error')
        return render_template('track_login.html')
    
    if not bcrypt.checkpw(password.encode('utf-8'), request_obj.tracking_password.encode('utf-8')):
        flash('Invalid Access Key. Please check your email for the correct key.', 'error')
        return render_template('track_login.html')
    
    # Authentication successful - store in session
    session['authenticated_orders'] = session.get('authenticated_orders', [])
    if order_id not in session['authenticated_orders']:
        session['authenticated_orders'].append(order_id)
    
    # Redirect to the actual tracking page
    return redirect(url_for('public.track_order', order_code=order_id))

@public_bp.route('/track/<order_code>')
def track_order(order_code):
    """Track order progress - requires authentication."""
    # Check if user is authenticated for this order
    authenticated_orders = session.get('authenticated_orders', [])
    if order_code not in authenticated_orders:
        # Check if user is logged in and owns this order
        if current_user.is_authenticated:
            try:
                request_id = int(order_code.split('-')[0])
                request_obj = Request.query.get(request_id)
                if request_obj and request_obj.user_id == current_user.id:
                    # User owns this order, allow access
                    pass
                else:
                    flash('Please authenticate to view this order.', 'info')
                    return redirect(url_for('public.track_order_login'))
            except:
                flash('Invalid order code.', 'error')
                return redirect(url_for('public.track_order_login'))
        else:
            flash('Please authenticate to view this order.', 'info')
            return redirect(url_for('public.track_order_login'))
    
    # Extract request ID from order code
    try:
        request_id = int(order_code.split('-')[0])
    except:
        flash('Invalid order code', 'error')
        return redirect(url_for('public.index'))
    
    # Get request
    request_obj = Request.query.get_or_404(request_id)
    
    # Verify order code
    if generate_order_code(request_obj) != order_code:
        flash('Invalid order code', 'error')
        return redirect(url_for('public.index'))
    
    # CHECK IF ORDER IS STILL IN QUEUE
    if request_obj.queue_position is not None and request_obj.queue_position > 0:
        # Order is still in queue - redirect to queue status page
        return redirect(url_for('public.queue_status', request_id=request_id))
    
    # Get progress steps
    progress_steps = request_obj.progress_steps.all()
    
    # If no progress steps, create default ones
    if not progress_steps:
        create_default_progress_steps(request_obj)
        progress_steps = request_obj.progress_steps.all()
    
    # Calculate overall progress based on step progress percentages
    if progress_steps:
        # Only first step should be completed initially (Order Received)
        # All other steps should be pending with 0% progress
        completed_steps = sum(1 for step in progress_steps if step.status == 'completed')
        in_progress_sum = sum(step.progress_percentage or 0 for step in progress_steps if step.status == 'in_progress')
        
        # Calculate overall progress properly
        if len(progress_steps) > 0:
            # Each completed step contributes equally, in-progress steps contribute partially
            step_weight = 100.0 / len(progress_steps)
            overall_progress = int((completed_steps * step_weight) + (in_progress_sum * step_weight / 100))
        else:
            overall_progress = 0
    else:
        overall_progress = 0
    
    # Get messages
    messages = request_obj.messages.all()
    
    # Mark notifications as read
    unread_notifications = Notification.query.filter_by(
        request_id=request_id, 
        is_read=False
    ).all()
    for notif in unread_notifications:
        notif.is_read = True
    db.session.commit()
    
    return render_template('order_tracking_new.html',
        request=request_obj,
        order_code=order_code,
        progress_steps=progress_steps,
        overall_progress=overall_progress,
        messages=messages
    )

@public_bp.route('/track/<order_code>/message', methods=['POST'])
def send_message(order_code):
    """Send message from client."""
    # Extract request ID from order code
    try:
        request_id = int(order_code.split('-')[0])
    except:
        return jsonify({'success': False, 'error': 'Invalid order code'}), 400
    
    request_obj = Request.query.get_or_404(request_id)
    
    # Verify order code
    if generate_order_code(request_obj) != order_code:
        return jsonify({'success': False, 'error': 'Invalid order code'}), 400
    
    message_content = request.form.get('message', '').strip()
    if not message_content:
        return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
    
    # Create message
    message = Message(
        request_id=request_id,
        sender_type='client',
        sender_name=request_obj.client_name,
        content=message_content
    )
    db.session.add(message)
    
    # Create notification for admin
    notification = Notification(
        request_id=request_id,
        type='message',
        title='New Message',
        content=f'New message from {request_obj.client_name}: {message_content[:50]}...',
        icon='info'
    )
    db.session.add(notification)
    
    db.session.commit()
    
    # Send email notification to admin
    try:
        send_message_notification_email(request_obj, message_content)
    except Exception as e:
        current_app.logger.warning(f'Failed to send message notification email: {e}')
    
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

# API Routes
@public_bp.route('/api/order/<order_code>/updates')
def get_order_updates(order_code):
    """Get real-time updates for order."""
    try:
        request_id = int(order_code.split('-')[0])
    except:
        return jsonify({'error': 'Invalid order code'}), 400
    
    request_obj = Request.query.get_or_404(request_id)
    
    # Verify order code
    if generate_order_code(request_obj) != order_code:
        return jsonify({'error': 'Invalid order code'}), 400
    
    last_message_id = request.args.get('last_id', 0, type=int)
    
    # Get new messages
    new_messages = Message.query.filter(
        Message.request_id == request_id,
        Message.id > last_message_id
    ).all()
    
    # Check for progress updates
    progress_updated = False
    latest_progress = OrderProgress.query.filter_by(request_id=request_id).order_by(
        OrderProgress.id.desc()
    ).first()
    
    if latest_progress and latest_progress.id > last_message_id:
        progress_updated = True
    
    return jsonify({
        'new_messages': len(new_messages) > 0,
        'messages': [{
            'id': msg.id,
            'content': msg.content,
            'sender_type': msg.sender_type,
            'sender_name': msg.sender_name,
            'created_at': msg.created_at.isoformat()
        } for msg in new_messages],
        'progress_updated': progress_updated
    })

@public_bp.route('/api/send_code', methods=['POST'])
def send_code():
    """Send OTP verification code (FREE - via EMAIL)."""
    try:
        from zetsu.sms_service import otp_service
        
        data = request.get_json()
        contact_info = data.get('contact')  # Can be phone or email
        email = data.get('email')  # Explicit email if provided
        phone = data.get('phone')  # Phone number
        
        # Prefer email if provided
        primary_contact = email if email else contact_info
        
        if not primary_contact:
            return jsonify({'success': False, 'error': 'Contact information required'}), 400
        
        # Store email in session for later use
        if email:
            session['user_email'] = email
        
        # Basic validation
        primary_contact = primary_contact.strip()
        if len(primary_contact) < 3:
            return jsonify({'success': False, 'error': 'Invalid contact information'}), 400
        
        # Clean up any expired OTPs
        otp_service.cleanup_expired()
        
        # Use phone as identifier but send to email if available
        identifier = phone if phone else primary_contact
        
        # Send OTP (prioritizes email)
        result = otp_service.send_otp(identifier, primary_contact)
        
        # Log for monitoring
        current_app.logger.info(f'OTP sent to {contact_info} via {result.get("mode", "unknown")} mode')
        
        # Prepare response
        response_data = {
            'success': result['success'],
            'message': result.get('message', 'Verification code sent'),
            'mode': result.get('mode', 'unknown')
        }
        
        # Include demo code only in console mode for testing
        if result.get('mode') == 'console':
            response_data['demo_code'] = result.get('demo_code')
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f'Error sending OTP: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@public_bp.route('/api/verify_code', methods=['POST'])
def verify_code():
    """Verify OTP code."""
    try:
        from zetsu.sms_service import otp_service
        
        data = request.get_json()
        code = data.get('code')
        contact_info = data.get('contact')
        
        if not code or not contact_info:
            return jsonify({'success': False, 'error': 'Code and contact information required'}), 400
        
        # Verify OTP using the new system
        result = otp_service.verify_otp(contact_info, code)
        
        if result['success']:
            # Mark as verified in session
            session['otp_verified'] = True
            session['verified_contact'] = contact_info
            
            return jsonify({
                'success': True, 
                'message': result.get('message', 'OTP verified successfully')
            })
        else:
            return jsonify({
                'success': False, 
                'error': result.get('error', 'Verification failed')
            }), 400
            
    except Exception as e:
        current_app.logger.error(f'Error verifying OTP: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

# Backward compatibility endpoints
@public_bp.route('/api/phone-verification/send', methods=['POST'])
def send_phone_verification():
    """Backward compatibility endpoint for phone verification."""
    data = request.get_json()
    phone = data.get('phone', '')
    # Forward to new endpoint
    return send_code()

@public_bp.route('/api/phone-verification/verify', methods=['POST'])
def verify_phone_code():
    """Backward compatibility endpoint for phone verification."""
    data = request.get_json()
    # Map old field names to new ones
    new_data = {
        'code': data.get('code'),
        'contact': data.get('phone')
    }
    request.get_json = lambda: new_data
    return verify_code()

@public_bp.route('/api/chatbot-submit-order', methods=['POST'])
def chatbot_submit_order():
    """API endpoint for chatbot to submit orders - WITH QUEUE SYSTEM AND VERIFICATION."""
    try:
        data = request.get_json()
        
        # Check if order is verified (from multi-step form)
        is_verified = data.get('verified', False)
        
        # Extract additional fields from verified form
        website_for = data.get('website_for', '')
        country = data.get('country', '')
        
        # If user is logged in, use their info
        if current_user.is_authenticated and isinstance(current_user, User):
            client_name = current_user.full_name or current_user.username or data.get('name', 'Chatbot User')
            client_email = current_user.email
            phone = current_user.phone or data.get('phone', 'Pending')
            user_id = current_user.id
        else:
            client_name = data.get('name', 'Chatbot User')
            client_email = data.get('email', 'pending@zetsuserv.com')
            phone = data.get('phone', 'Pending')
            user_id = None
        
        # If verified order, ensure required fields
        if is_verified:
            if not all([website_for, country, phone != 'Pending']):
                return jsonify({'success': False, 'error': 'Missing required verified information'}), 400
            # Build enhanced details
            details = f"Order submitted via AI Chat Assistant (Verified)\n\n"
            details += f"Website For: {website_for}\n"
            details += f"Country: {country}\n"
            details += f"Phone: {phone}\n\n"
            details += f"Project Details: {data.get('details', 'No additional details')}"
        else:
            details = f"Order submitted via AI Chat Assistant\n\n{data.get('details', 'No additional details')}"
        
        # CHECK QUEUE POSITION - CRITICAL FOR QUEUE SYSTEM
        # Count active orders (queue_position is None or 0)
        active_count = Request.query.filter(
            db.or_(
                Request.queue_position.is_(None),
                Request.queue_position == 0
            )
        ).count()
        
        # Get highest queue position
        max_queue = db.session.query(db.func.max(Request.queue_position)).scalar() or 0
        
        # Determine queue position for new order
        # IMPORTANT: Only the very first order when NO active orders exist should be activated
        if active_count == 0:
            # No active orders, this will be activated immediately
            queue_pos = 1  # Will be activated
        else:
            # There are active orders, must join queue
            queue_pos = max_queue + 1  # Add to end of queue
        
        # Create new request from chatbot data WITH QUEUE POSITION
        new_request = Request(
            user_id=user_id,  # Link to user if logged in
            client_name=client_name,
            client_email=client_email,
            phone=phone,
            project_title=data.get('title', data.get('projectName', 'New Project Request')),
            project_type=data.get('type', 'business').lower().replace(' ', '_'),
            pages_required=int(data.get('pages', 5)),
            budget=data.get('budget', '$1000-5000'),
            details=details,
            status='new',
            queue_position=queue_pos  # SET QUEUE POSITION
        )
        
        # Save to database
        db.session.add(new_request)
        db.session.commit()
        
        # Generate tracking code and password
        tracking_code = generate_order_code(new_request)
        tracking_password = generate_tracking_password()
        new_request.tracking_code = tracking_code
        new_request.tracking_password = bcrypt.hashpw(tracking_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.session.commit()
        
        # Create initial progress steps
        create_default_progress_steps(new_request)
        
        # CHECK IF ORDER SHOULD BE ACTIVATED
        # Only activate if there are NO other active orders
        if active_count == 0:
            # ACTIVATE IMMEDIATELY - No other active orders
            new_request.queue_position = None
            new_request.queue_activated_at = datetime.now()
            db.session.commit()
            
            # Send activation email with tracking code and password
            try:
                send_queue_activation_email(new_request, tracking_code, tracking_password)
                if new_request.client_email != 'pending@zetsuserv.com':
                    send_tracking_code_email(new_request, tracking_code, tracking_password)
            except Exception as e:
                current_app.logger.warning(f'Failed to send activation email: {e}')
            
            # Return with tracking code (first in queue)
            return jsonify({
                'success': True,
                'tracking_code': tracking_code,
                'order_id': new_request.id,
                'queue_position': 0,  # Active
                'is_active': True,
                'message': "Great news! You're first in queue - work begins immediately!"
            })
        else:
            # IN QUEUE - Must wait for others
            # Send notification email WITHOUT tracking code
            try:
                send_notification_email(new_request)
            except Exception as e:
                current_app.logger.warning(f'Failed to send notification email: {e}')
            
            # Calculate actual position
            orders_ahead = queue_pos - 1 if active_count > 0 else queue_pos - 1
            
            # Return WITHOUT tracking code (in queue)
            return jsonify({
                'success': True,
                'tracking_code': None,  # NO TRACKING CODE FOR QUEUED ORDERS
                'order_id': new_request.id,
                'queue_position': orders_ahead + 1,
                'is_active': False,
                'orders_ahead': orders_ahead,
                'message': f"Order submitted! You are #{orders_ahead + 1} in queue. You'll receive an email with tracking code when it's your turn."
            })
        
    except Exception as e:
        current_app.logger.error(f'Error submitting chatbot order: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@public_bp.route('/api/user/settings', methods=['POST'])
@login_required
def update_user_settings():
    """Update user settings."""
    try:
        data = request.get_json()
        
        if 'enable_profile_video' in data:
            current_user.enable_profile_video = bool(data['enable_profile_video'])
        
        if 'video_overlay_strength' in data:
            strength = int(data['video_overlay_strength'])
            # Clamp between 0 and 100
            current_user.video_overlay_strength = max(0, min(100, strength))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
    except Exception as e:
        current_app.logger.error(f'Error updating user settings: {e}')
        return jsonify({'success': False, 'error': 'Failed to update settings'}), 500

@public_bp.route('/api/request-access-key/<int:order_id>', methods=['POST'])
@login_required
def request_access_key(order_id):
    """Generate or resend access key for user's own order."""
    try:
        # Import at function level to avoid circular imports
        from flask_login import current_user
        
        # Get the order and verify ownership
        order = Request.query.get(order_id)
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        # Check if user owns this order
        if order.user_id != current_user.id:
            current_app.logger.warning(f'User {current_user.id} tried to access order {order_id} owned by user {order.user_id}')
            return jsonify({'success': False, 'error': 'You do not have permission to access this order'}), 403
        
        # Generate tracking code if not set
        tracking_code = order.tracking_code or generate_order_code(order)
        if not order.tracking_code:
            order.tracking_code = tracking_code
            db.session.commit()
        
        # Generate or regenerate password
        tracking_password = generate_tracking_password()
        order.tracking_password = bcrypt.hashpw(
            tracking_password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        db.session.commit()
        
        current_app.logger.info(f'Generated new access key for order {order_id}: {tracking_password}')
        
        # Send email with access key
        try:
            send_tracking_code_email(order, tracking_code, tracking_password)
            current_app.logger.info(f'Email sent successfully to {order.client_email}')
        except Exception as email_error:
            current_app.logger.error(f'Failed to send email: {email_error}')
            # Still return success since we generated the password
            return jsonify({
                'success': True,
                'message': f'Access key generated: {tracking_password}. Note: Email delivery failed, please save this key.',
                'generated': True,
                'access_key': tracking_password  # Show the key in case email fails
            })
        
        return jsonify({
            'success': True,
            'message': f'Access key sent to {order.client_email}',
            'generated': True
        })
        
    except Exception as e:
        current_app.logger.error(f'Error requesting access key: {str(e)}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Failed to process request: {str(e)}'}), 500

@public_bp.route('/api/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Upload user avatar."""
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Check if file is an image
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid file type. Please upload an image.'}), 400
    
    # Save the file
    try:
        # Generate unique filename
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(file.filename)
        filename = f'avatar_{current_user.id}_{random_hex}{f_ext}'
        filename = secure_filename(filename)
        
        # Ensure avatar directory exists in static folder
        avatar_path = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars')
        os.makedirs(avatar_path, exist_ok=True)
        
        # Delete old avatar if exists
        if current_user.avatar_url and current_user.avatar_url.startswith('/static/uploads/avatars/'):
            old_filename = current_user.avatar_url.split('/')[-1]
            old_path = os.path.join(avatar_path, old_filename)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass  # Ignore errors when deleting old avatar
        
        # Save file
        file_path = os.path.join(avatar_path, filename)
        file.save(file_path)
        
        # Update user's avatar URL (relative path for serving)
        current_user.avatar_url = '/static/uploads/avatars/' + filename
        db.session.commit()
        
        return jsonify({
            'success': True,
            'avatar_url': current_user.avatar_url,
            'message': 'Avatar uploaded successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error uploading avatar: {e}')
        return jsonify({'success': False, 'error': 'Failed to upload avatar'}), 500

@public_bp.route('/api/ai-assistant', methods=['POST'])
def ai_assistant():
    """AI assistant endpoint with Gemini integration - now queue-aware."""
    data = request.json
    user_message = data.get('message', '')
    order_code = data.get('order_code', '')
    
    # Initialize variables
    queue_info = ""
    request_obj = None
    actual_position = 0
    
    # Check queue status if order code provided
    if order_code:
        try:
            request_id = int(order_code.split('-')[0])
            request_obj = Request.query.get(request_id)
            if request_obj:
                # Check queue position
                if request_obj.queue_position and request_obj.queue_position > 0:
                    # Count how many are ahead
                    ahead = Request.query.filter(
                        Request.queue_position.isnot(None),
                        Request.queue_position > 0,
                        Request.queue_position < request_obj.queue_position
                    ).count()
                    actual_position = ahead + 1
                    
                    # Calculate estimated wait time and detailed info
                    if ahead == 0:
                        wait_time_info = "You're next! Your order will be activated very soon."
                    elif ahead == 1:
                        wait_time_info = "1 customer submitted before you, so you must wait for their order to complete."
                    else:
                        wait_time_info = f"{ahead} customers submitted before you, so you must wait for all of them to complete."
                    
                    queue_info = f"""\n📊 YOUR QUEUE STATUS:
• Position: #{actual_position} in queue
• Orders ahead: {ahead}
• {wait_time_info}
• You'll receive an email with tracking code when it's your turn.
• This is fair - everyone who orders after someone else must wait!"""
                elif request_obj.queue_position == 0 or request_obj.queue_position is None:
                    queue_info = "\n✅ ACTIVE STATUS: Your order is currently being worked on! You should have received your tracking code."
        except:
            pass
    
    # Enhanced queue explanation for new customers
    queue_explanation = """\n📋 HOW OUR QUEUE SYSTEM WORKS:
1️⃣ First person to submit gets immediate tracking code - work begins right away
2️⃣ Second person must wait for first to complete
3️⃣ Third person must wait for first AND second to complete
4️⃣ Each new order joins the back of the queue
5️⃣ When your turn comes, you get email with tracking code automatically

⚠️ IMPORTANT: If someone submitted before you, you MUST wait. This is fair for everyone!"""
    
    # Default responses for fallback - enhanced with queue rules
    default_responses = [
        f"I understand you're asking about your order. {queue_info if queue_info else queue_explanation} Remember: If others ordered before you, you must wait your turn. It's only fair!",
        f"Thank you for your inquiry! {queue_info if queue_info else 'Here is how it works:'} When someone submits an order before you, you wait in queue. First come, first served - no exceptions!",
        f"Let me explain the waiting: {queue_info if queue_info else queue_explanation} New customers who order after someone else ALWAYS wait their turn. The person who ordered first gets served first.",
        f"About why you're waiting: {queue_info if queue_info else 'Simple rule:'} Someone ordered before you = you wait for them to finish. That's our fair queue system!",
        f"Regarding the queue: {queue_info if queue_info else queue_explanation} Every new order waits for ALL previous orders. This ensures fairness and quality for everyone."
    ]
    
    response = ""
    
    # Try to use Gemini AI if API key is available
    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if gemini_api_key and gemini_api_key != 'AIzaSyB7KvZHc2YNEw8B0VfQqXKxLz5JvZ9mXXX':  # Replace with actual key
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            
            # Create context for the AI
            context = f"""
            You are a helpful customer support assistant for ZetsuServ, a professional web development company.
            Be friendly, professional, and helpful. Keep responses concise but informative.
            
            CRITICAL QUEUE SYSTEM RULES YOU MUST EXPLAIN:
            1. We work on ONE order at a time - never multiple orders simultaneously
            2. If Customer A submits before Customer B, then Customer B MUST wait for Customer A to complete
            3. Only the FIRST person in queue gets immediate tracking code
            4. Everyone else waits in line until it's their turn
            5. When someone's turn arrives, they get email with tracking code automatically
            6. This is STRICT first-come, first-served - absolutely no queue jumping
            
            When users ask why they're waiting or don't have tracking code:
            - Clearly explain: "You're waiting because other customers submitted their orders before you"
            - Tell them their exact position and who's ahead
            - Emphasize this is fair - if they ordered second, they wait for first
            - Reassure them about automatic email notification
            
            Current order information:
            {queue_info if queue_info else "No specific order loaded."}
            
            Customer message: {user_message}
            """
            
            if order_code and request_obj:
                # Add order details to context
                queue_status = "Active (being worked on)" if (request_obj.queue_position is None or request_obj.queue_position == 0) else f"In Queue (Position #{actual_position if actual_position > 0 else request_obj.queue_position})"
                
                # Add clear waiting reason if in queue
                waiting_reason = ""
                if request_obj.queue_position and request_obj.queue_position > 0:
                    ahead = Request.query.filter(
                        Request.queue_position.isnot(None),
                        Request.queue_position > 0,
                        Request.queue_position < request_obj.queue_position
                    ).count()
                    if ahead > 0:
                        waiting_reason = f"\n                    - WHY WAITING: {ahead} customer{'s' if ahead != 1 else ''} submitted before this customer - they must wait their turn!"
                
                context += f"""
                Order details:
                - Project: {request_obj.project_title}
                - Type: {request_obj.get_project_type_display()}
                - Status: {request_obj.get_status_display()}
                - Queue Status: {queue_status}{waiting_reason}
                - Created: {request_obj.created_at.strftime('%B %d, %Y')}
                
                IMPORTANT: If this order is in queue, you MUST explain that they're waiting because other customers ordered before them. This is how queues work - first come, first served!
                """
            
            model = genai.GenerativeModel('gemini-pro')
            ai_response = model.generate_content(context)
            response = ai_response.text
            
            # Add queue-specific reminder if order is in queue
            if order_code and request_obj:
                if request_obj.queue_position and request_obj.queue_position > 0:
                    ahead = Request.query.filter(
                        Request.queue_position.isnot(None),
                        Request.queue_position > 0,
                        Request.queue_position < request_obj.queue_position
                    ).count()
                    if ahead > 0:
                        response += f"\n\n⏳ **Why you're waiting:** {ahead} customer{'s' if ahead != 1 else ''} ordered before you. In a queue, everyone who comes later must wait for those who came first. You'll get an email with tracking code when it's your turn!"
                    else:
                        response += "\n\n🎯 **Good news:** You're next in line! Your order will be activated very soon. Watch your email!"
                elif request_obj.queue_position == 0 or request_obj.queue_position is None:
                    response += "\n\n✅ **Order Status:** Your order is active and being worked on. Check your email for the tracking code."
            
        except ImportError:
            # google.generativeai not installed
            current_app.logger.info('Gemini AI library not installed, using default responses')
            import random
            response = random.choice(default_responses)
        except Exception as e:
            # API error or invalid key
            current_app.logger.warning(f'Gemini AI error: {e}')
            import random
            response = random.choice(default_responses)
    else:
        # No API key configured
        import random
        response = random.choice(default_responses)
    
    return jsonify({'response': response})

# ------------------------------
# Email Verification Routes
# ------------------------------

@public_bp.route('/verify-email')
def verify_email():
    """Show email verification page."""
    # Ensure we know which user is pending verification
    pending_id = session.get('pending_verify_user_id')
    if not pending_id:
        flash('No verification pending. Please register or login.', 'info')
        return redirect(url_for('public.user_login'))

    user = User.query.get(pending_id)
    if not user:
        session.pop('pending_verify_user_id', None)
        flash('User not found. Please register again.', 'error')
        return redirect(url_for('public.user_register'))
    
    # Check if already verified
    if user.email_verified:
        session.pop('pending_verify_user_id', None)
        login_user(user, remember=True)
        flash('Your email is already verified!', 'success')
        return redirect(url_for('public.user_dashboard'))

    # Show verification page
    return render_template('email_verify.html', user_email=user.email)

@public_bp.route('/verify-email/submit', methods=['POST'])
def verify_email_submit():
    """Handle verification code submission."""
    from datetime import datetime
    
    # Ensure we know which user is pending verification
    pending_id = session.get('pending_verify_user_id')
    if not pending_id:
        flash('No verification pending. Please register or login.', 'info')
        return redirect(url_for('public.user_login'))

    user = User.query.get(pending_id)
    if not user:
        session.pop('pending_verify_user_id', None)
        flash('User not found. Please register again.', 'error')
        return redirect(url_for('public.user_register'))
    
    # Get code from form
    code = request.form.get('code', '').strip()
    
    # Validate code format
    if not code or not code.isdigit() or len(code) != 6:
        flash('Please enter a valid 6-digit code.', 'error')
        return redirect(url_for('public.verify_email'))
    
    # Check if code exists and not expired
    if not user.email_verification_code_hash or not user.email_verification_expires_at:
        flash('No verification code found. Please request a new code.', 'error')
        return redirect(url_for('public.verify_email'))
    
    if user.email_verification_expires_at < datetime.utcnow():
        flash('Verification code has expired. Please request a new code.', 'error')
        return redirect(url_for('public.verify_email'))
    
    # Verify the code
    if bcrypt.checkpw(code.encode('utf-8'), user.email_verification_code_hash.encode('utf-8')):
        # Success - mark as verified
        user.email_verified = True
        user.email_verification_code_hash = None
        user.email_verification_expires_at = None
        db.session.commit()
        
        # Clear session and log user in
        session.pop('pending_verify_user_id', None)
        login_user(user, remember=True)
        user.update_last_login()
        
        flash('Email verified successfully! Welcome to ZetsuServ!', 'success')
        return redirect(url_for('public.user_dashboard'))
    else:
        flash('Invalid verification code. Please try again.', 'error')
        return redirect(url_for('public.verify_email'))


@public_bp.route('/verify-email/resend', methods=['POST'])
def resend_verification():
    """Resend verification code with rate limiting."""
    from datetime import datetime, timedelta
    
    pending_id = session.get('pending_verify_user_id')
    if not pending_id:
        return jsonify({'success': False, 'error': 'No verification pending.'}), 400
    
    user = User.query.get(pending_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404

    # Check rate limit: 60 seconds between sends
    if user.last_verification_sent_at:
        time_since_last = (datetime.utcnow() - user.last_verification_sent_at).total_seconds()
        if time_since_last < 60:
            remaining = 60 - int(time_since_last)
            return jsonify({
                'success': False, 
                'error': 'Please wait before resending.', 
                'retry_after': remaining
            }), 429

    try:
        # Generate new code
        code = generate_verification_code()
        code_hash = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Update user with new code
        user.email_verification_code_hash = code_hash
        user.email_verification_expires_at = datetime.utcnow() + timedelta(minutes=10)
        user.last_verification_sent_at = datetime.utcnow()
        db.session.commit()
        
        # Send email
        send_verification_code_email(user, code)
        
        return jsonify({'success': True, 'message': 'Verification code sent successfully!'})
    except Exception as e:
        current_app.logger.error(f'Failed to resend verification code: {e}')
        return jsonify({'success': False, 'error': 'Failed to send code. Please try again.'}), 500

def generate_order_code(request_obj):
    """Generate unique order tracking code."""
    # Create a unique code based on request ID and email
    hash_input = f"{request_obj.id}-{request_obj.client_email}"
    hash_code = hashlib.md5(hash_input.encode()).hexdigest()[:6].upper()
    return f"{request_obj.id:06d}-{hash_code}"

def create_default_progress_steps(request_obj):
    """Create default progress steps for a new request."""
    steps = [
        {
            'step_number': 1,
            'step_name': 'Order Received',
            'step_description': 'Your order has been received and is being reviewed by our team.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 2,
            'step_name': 'Requirements Analysis',
            'step_description': 'Our team is analyzing your requirements and preparing a development plan.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 3,
            'step_name': 'Design Phase',
            'step_description': 'Creating mockups and design concepts for your approval.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 4,
            'step_name': 'Development',
            'step_description': 'Building your website with all requested features and functionality.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 5,
            'step_name': 'Testing & Optimization',
            'step_description': 'Ensuring everything works perfectly across all devices and browsers.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 6,
            'step_name': 'Domain & Hosting Setup',
            'step_description': 'Configuring your domain and hosting environment.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 7,
            'step_name': 'Final Review',
            'step_description': 'Final quality check and client approval.',
            'status': 'pending',
            'progress_percentage': 0
        },
        {
            'step_number': 8,
            'step_name': 'Launch',
            'step_description': 'Your website is live and ready for the world!',
            'status': 'pending',
            'progress_percentage': 0
        }
    ]
    
    for step_data in steps:
        step = OrderProgress(
            request_id=request_obj.id,
            **step_data
        )
        db.session.add(step)
    
    db.session.commit()

def send_message_notification_email(request_obj, message_content):
    """Send email notification for new message."""
    try:
        from flask_mail import Message
        from zetsu import mail
        
        # Check if mail is available
        if not mail:
            current_app.logger.warning('Mail extension not initialized')
            return
        
        username = current_app.config.get('MAIL_USERNAME')
        if not username:
            current_app.logger.warning('MAIL_USERNAME not configured; skipping send_message_notification_email')
            return
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or username
        if str(current_app.config.get('MAIL_SERVER', '')).endswith('gmail.com'):
            sender_email = username
        
        msg = Message(
            subject=f'New Message for Order #{request_obj.id:06d}',
            sender=sender_email,
            recipients=[current_app.config['ADMIN_EMAIL']]
        )
        
        msg.body = f"""
        New message received from client:
        
        Client: {request_obj.client_name}
        Project: {request_obj.project_title}
        
        Message:
        {message_content}
        
        View in admin dashboard: {url_for('admin.view_request', id=request_obj.id, _external=True)}
        """
        
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send message notification email: {e}')

def send_tracking_code_email(request_obj, tracking_code, tracking_password=None):
    """Send tracking code and password to client."""
    try:
        from flask_mail import Message
        from zetsu import mail
        
        # Check if mail is available
        if not mail:
            current_app.logger.warning('Mail extension not initialized')
            return
        
        username = current_app.config.get('MAIL_USERNAME')
        if not username:
            current_app.logger.warning('MAIL_USERNAME not configured; skipping send_tracking_code_email')
            return
        # For Gmail, always use the authenticated username as sender
        sender_email = username
        
        msg = Message(
            subject=f'Your ZetsuServ Order Tracking Code - {tracking_code}',
            sender=sender_email,
            recipients=[request_obj.client_email]
        )
        
        # Generate tracking URL - handle cases where we're outside request context
        try:
            tracking_url = url_for('public.track_order_login', _external=True)
        except:
            # Fallback URL if we're outside request context
            tracking_url = 'http://127.0.0.1:5000/track'
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">Thank You for Your Order!</h1>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Dear {request_obj.client_name},</p>
                
                <p>We have received your request for <strong>{request_obj.project_title}</strong> and our team is already working on it!</p>
                
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #666;">Your Tracking Code:</p>
                    <h2 style="color: #667eea; margin: 10px 0; font-size: 28px;">{tracking_code}</h2>
                    {f'''<p style="margin: 10px 0 0; color: #666;">Access Key:</p>
                    <h3 style="color: #764ba2; margin: 5px 0; font-size: 20px; font-family: monospace;">{tracking_password}</h3>
                    <p style="margin: 10px 0 0; color: #999; font-size: 12px;">⚠️ Keep this access key secure. You'll need both the tracking code and access key to view your order.</p>''' if tracking_password else ''}
                </div>
                
                <p>You can track your order progress anytime by visiting:</p>
                <p style="text-align: center;">
                    <a href="{tracking_url}" style="display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Track Your Order</a>
                </p>
                
                <h3 style="color: #333; margin-top: 30px;">What Happens Next?</h3>
                <ul style="color: #666; line-height: 1.8;">
                    <li>Our team will review your requirements within 24 hours</li>
                    <li>You'll receive updates at every major milestone</li>
                    <li>You can send messages and ask questions through the tracking page</li>
                    <li>We'll notify you via email for important updates</li>
                </ul>
                
                <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #666; font-size: 14px;">
                    If you have any questions, feel free to reply to this email or use the messaging system on your tracking page.
                </p>
                
                <p style="color: #666;">Best regards,<br><strong>The ZetsuServ Team</strong></p>
            </div>
        </div>
        """
        
        msg.body = f"""
        Dear {request_obj.client_name},
        
        Thank you for choosing ZetsuServ!
        
        We have received your request for {request_obj.project_title}.
        
        Your tracking code is: {tracking_code}
        {f'Access key: {tracking_password}' if tracking_password else ''}
        
        Track your order at: {tracking_url}
        {f'Note: You will need both the tracking code and access key to view your order.' if tracking_password else ''}
        
        What happens next:
        - Our team will review your requirements within 24 hours
        - You'll receive updates at every major milestone
        - You can send messages through the tracking page
        
        Best regards,
        The ZetsuServ Team
        """
        
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send tracking code email: {e}')

# User Authentication Routes
@public_bp.route('/register', methods=['GET', 'POST'])
def user_register():
    """User registration with email verification."""
    if current_user.is_authenticated:
        return redirect(url_for('public.user_dashboard'))
    
    form = UserRegistrationForm()
    
    if form.validate_on_submit():
        # Check if username exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists. Please choose another.', 'error')
            return render_template('user_register.html', form=form)
        
        # Check if email exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered. Please login or use another email.', 'error')
            return render_template('user_register.html', form=form)
        
        # Create new user (unverified)
        password_hash = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=password_hash.decode('utf-8'),
            full_name=form.full_name.data,
            phone=form.phone.data,
            company=form.company.data,
            email_verified=False
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Generate and send verification code
        try:
            code = generate_verification_code()
            # Store hash and expiry (10 minutes)
            from datetime import datetime, timedelta
            code_hash = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user.email_verification_code_hash = code_hash
            user.email_verification_expires_at = datetime.utcnow() + timedelta(minutes=10)
            user.last_verification_sent_at = datetime.utcnow()
            db.session.commit()
            
            send_verification_code_email(user, code)
        except Exception as e:
            current_app.logger.error(f'Failed to send verification email: {e}')
            flash('Failed to send verification email. Please try again later.', 'error')
            return render_template('user_register.html', form=form)
        
        # Set session state for verification page
        session['pending_verify_user_id'] = user.id
        
        flash('We\'ve sent a 6-digit verification code to your email. Please verify to complete registration.', 'info')
        return redirect(url_for('public.verify_email'))
    
    return render_template('user_register.html', form=form)

@public_bp.route('/login', methods=['GET', 'POST'])
def user_login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('public.user_dashboard'))
    
    form = UserLoginForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and bcrypt.checkpw(form.password.data.encode('utf-8'), user.password_hash.encode('utf-8')):
            if not user.email_verified:
                # Send a fresh code if previous expired or missing
                try:
                    from datetime import datetime, timedelta
                    need_new_code = True
                    if user.email_verification_expires_at and user.email_verification_expires_at > datetime.utcnow():
                        need_new_code = False
                    if need_new_code:
                        code = generate_verification_code()
                        user.email_verification_code_hash = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        user.email_verification_expires_at = datetime.utcnow() + timedelta(minutes=10)
                        user.last_verification_sent_at = datetime.utcnow()
                        db.session.commit()
                        send_verification_code_email(user, code)
                except Exception as e:
                    current_app.logger.warning(f'Failed to (re)send verification code: {e}')
                session['pending_verify_user_id'] = user.id
                flash('Please verify your email to continue. We\'ve sent you a verification code.', 'warning')
                return redirect(url_for('public.verify_email'))
            
            login_user(user, remember=form.remember_me.data)
            user.update_last_login()
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('public.user_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
    
    return render_template('user_login.html', form=form)

@public_bp.route('/logout')
@login_required
def user_logout():
    """User logout."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('public.index'))

@public_bp.route('/dashboard')
@login_required
def user_dashboard():
    """User dashboard."""
    # Check if the current user is an admin (AdminUser)
    if isinstance(current_user, AdminUser):
        # Redirect admin to admin dashboard
        return redirect(url_for('admin.dashboard'))
    
    # Check if current_user is actually a regular User
    if not isinstance(current_user, User):
        # If not a regular user, redirect to appropriate page
        flash('Please login as a user to access the dashboard.', 'info')
        return redirect(url_for('public.user_login'))
    
    # Get user orders
    orders = current_user.requests.order_by(Request.created_at.desc()).all()
    
    # Calculate stats
    total_orders = len(orders)
    active_orders = sum(1 for o in orders if o.status in ['new', 'in_progress'])
    completed_orders = sum(1 for o in orders if o.status in ['delivered', 'closed'])
    
    # Count unread messages
    unread_messages = 0
    for order in orders:
        unread_messages += order.messages.filter_by(sender_type='admin', is_read=False).count()
    
    return render_template('user_dashboard.html',
        orders=orders,
        total_orders=total_orders,
        active_orders=active_orders,
        completed_orders=completed_orders,
        unread_messages=unread_messages,
        generate_tracking_code=generate_order_code
    )

def send_welcome_email(user):
    """Send welcome email to new user."""
    try:
        from flask_mail import Message as MailMessage, Mail
        
        mail = Mail(current_app)
        
        username = current_app.config.get('MAIL_USERNAME')
        if not username:
            current_app.logger.warning('MAIL_USERNAME not configured; skipping send_welcome_email')
            return
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or username
        if str(current_app.config.get('MAIL_SERVER', '')).endswith('gmail.com'):
            sender_email = username
        
        msg = MailMessage(
            subject='Welcome to ZetsuServ!',
            sender=sender_email,
            recipients=[user.email]
        )
        
        msg.html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">Welcome to ZetsuServ!</h1>
            </div>
            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Hi {user.full_name or user.username},</p>
                
                <p>Thank you for creating an account with ZetsuServ! We're excited to have you on board.</p>
                
                <h3>What you can do now:</h3>
                <ul>
                    <li>Submit new project requests</li>
                    <li>Track all your orders in one place</li>
                    <li>Communicate directly with our team</li>
                    <li>Get real-time project updates</li>
                </ul>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{url_for('public.user_dashboard', _external=True)}" style="display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Go to Dashboard</a>
                </p>
                
                <p style="color: #666; margin-top: 30px;">Best regards,<br><strong>The ZetsuServ Team</strong></p>
            </div>
        </div>
        """
        
        msg.body = f"""
        Hi {user.full_name or user.username},
        
        Thank you for creating an account with ZetsuServ!
        
        You can now:
        - Submit new project requests
        - Track all your orders
        - Communicate with our team
        - Get real-time updates
        
        Visit your dashboard: {url_for('public.user_dashboard', _external=True)}
        
        Best regards,
        The ZetsuServ Team
        """
        
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send welcome email: {e}')

def send_notification_email(request_obj):
    """Send notification email to admin about new request."""
    # Placeholder function for email notification
    # In production, implement using Flask-Mail
    try:
        from flask_mail import Message, Mail
        
        mail = Mail(current_app)
        
        username = current_app.config.get('MAIL_USERNAME')
        if not username:
            # Mail not configured, skip
            current_app.logger.info('MAIL_USERNAME not set; skipping send_notification_email')
            return
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or username
        if str(current_app.config.get('MAIL_SERVER', '')).endswith('gmail.com'):
            sender_email = username
        
        msg = Message(
            subject=f'New Service Request: {request_obj.project_title}',
            sender=sender_email,
            recipients=[current_app.config['ADMIN_EMAIL']]
        )
        
        msg.body = f"""
        New service request received:
        
        Client: {request_obj.client_name}
        Email: {request_obj.client_email}
        Phone: {request_obj.phone}
        
        Project: {request_obj.project_title}
        Type: {request_obj.get_project_type_display()}
        Pages: {request_obj.pages_required}
        Budget: {request_obj.budget}
        
        Details:
        {request_obj.details}
        
        View in admin dashboard: {url_for('admin.view_request', id=request_obj.id, _external=True)}
        """
        
        mail.send(msg)
    except ImportError:
        # Flask-Mail not installed, skip email notification
        current_app.logger.info(f'Email notification skipped - Flask-Mail not installed')

# ------------------------------
# Email verification helpers
# ------------------------------

def generate_verification_code():
    """Generate a 6-digit verification code as a string."""
    import secrets
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def generate_tracking_password():
    """Generate a secure 8-character password for order tracking."""
    import secrets
    import string
    # Use letters and digits for better readability
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(8))
    return password


def send_queue_activation_email(request_obj, tracking_code, tracking_password=None):
    """Send email when user's turn arrives in queue with access key."""
    try:
        from flask_mail import Message as MailMessage
        from zetsu import mail
        
        # Check if mail is available
        if not mail:
            current_app.logger.warning('Mail extension not initialized')
            return
        
        username = current_app.config.get('MAIL_USERNAME')
        if not username:
            current_app.logger.warning('MAIL_USERNAME not configured; cannot send queue activation email')
            return
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or username
        if str(current_app.config.get('MAIL_SERVER', '')).endswith('gmail.com'):
            sender_email = username

        # Generate tracking URL - handle cases where we're outside request context
        try:
            tracking_url = url_for('public.track_order_login', _external=True)
        except:
            # Fallback URL if we're outside request context
            tracking_url = 'http://127.0.0.1:5000/track'
        
        msg = MailMessage(
            subject='🎉 Your turn has arrived! Your project is now active - ZetsuServ',
            sender=sender_email,
            recipients=[request_obj.client_email]
        )
        
        msg.html = f"""
        <div style="font-family: Inter, Arial, sans-serif; max-width: 640px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
            <div style="padding: 28px; background: #10b981; color: white; border-radius: 12px 12px 0 0; text-align: center;">
                <h2 style="margin: 0; font-weight: 700; font-size: 24px;">🎉 Hey Champ, You're First!</h2>
            </div>
            <div style="padding: 24px;">
                <p style="color: #0f172a; font-size: 16px;">Great news!</p>
                <p style="color: #334155;">Your project <strong>{request_obj.project_title}</strong> is now active and our team has started working on it.</p>
                
                <div style="margin: 24px 0; padding: 20px; background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 8px; text-align: center;">
                    <p style="color: #64748b; margin: 0 0 8px 0; font-size: 14px;">Your Tracking Number:</p>
                    <p style="font-family: monospace; font-size: 20px; font-weight: bold; color: #0f172a; margin: 0;">{tracking_code}</p>
                    {f'''<p style="color: #64748b; margin: 12px 0 8px 0; font-size: 14px;">Access Key:</p>
                    <p style="font-family: monospace; font-size: 18px; font-weight: bold; color: #764ba2; margin: 0;">{tracking_password}</p>
                    <p style="color: #94a3b8; margin: 8px 0 0 0; font-size: 12px;">🔒 Keep this access key secure</p>''' if tracking_password else ''}
                </div>
                
                <p style="color: #475569;">You can now track your project progress in real-time:</p>
                <p style="margin-top: 16px; text-align: center;">
                    <a href="{tracking_url}" style="display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">Track Your Project</a>
                </p>
                
                <hr style="margin: 24px 0; border: none; border-top: 1px solid #e2e8f0;">
                <p style="color: #0f172a; font-size: 14px; margin-top: 16px;"><strong>— The ZetsuServ Team</strong><br>
                <span style="color:#64748b;">We'll keep you updated on every milestone!</span></p>
            </div>
        </div>
        """
        
        msg.body = (
            f"Great news! Your project is now active!\n\n"
            f"Project: {request_obj.project_title}\n"
            f"Tracking Number: {tracking_code}\n\n"
            f"Track your project: {tracking_url}\n\n"
            f"— The ZetsuServ Team"
        )
        
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send queue activation email: {e}')

def send_verification_code_email(user, code):
    """Send the email verification code to the user's email address."""
    try:
        from flask_mail import Message as MailMessage
        from zetsu import mail
        
        # Check if mail is available
        if not mail:
            current_app.logger.warning('Mail extension not initialized')
            return
        
        username = current_app.config.get('MAIL_USERNAME')
        if not username:
            current_app.logger.warning('MAIL_USERNAME not configured; cannot send verification email')
            return
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER') or username
        if str(current_app.config.get('MAIL_SERVER', '')).endswith('gmail.com'):
            sender_email = username

        subject = 'Action Required: Verify your email to activate your ZetsuServ account'
        msg = MailMessage(
            subject=subject,
            sender=sender_email,
            recipients=[user.email]
        )

        # Split code into spaced digits for visual emphasis
        spaced_code = ' '.join(list(code))
        
        # Generate verification URL - handle cases where we're outside request context
        try:
            verification_url = url_for('public.verify_email', _external=True)
        except:
            # Fallback URL if we're outside request context
            verification_url = 'http://127.0.0.1:5000/verify'

        msg.html = f"""
        <div style="font-family: Inter, Arial, sans-serif; max-width: 640px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;">
            <div style="padding: 28px; background: #0ea5e9; color: white; border-radius: 12px 12px 0 0;">
                <h2 style="margin: 0; font-weight: 700;">Verify your email</h2>
                <p style="margin: 6px 0 0; opacity: 0.95;">From the ZetsuServ Team</p>
            </div>
            <div style="padding: 24px;">
                <p style="color: #0f172a; font-size: 16px;">Hi {user.full_name or user.username},</p>
                <p style="color: #334155;">Thanks for creating your account. Please enter the following 6-digit verification code to activate your account:</p>
                <div style="margin: 18px 0; text-align: center;">
                    <div style="display: inline-block; padding: 14px 20px; font-size: 28px; font-weight: 800; letter-spacing: 10px; color: #111827; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 10px;">{spaced_code}</div>
                </div>
                <p style="color: #475569;">This code expires in <strong>10 minutes</strong>. For your security, do not share it with anyone.</p>
                <p style="color: #475569; margin-top: 12px;">If you are ready, open the verification page and enter the code:</p>
                <p style="margin-top: 8px; text-align: center;">
                    <a href="{verification_url}" style="display: inline-block; padding: 12px 20px; background: #0ea5e9; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">Open Verification Page</a>
                </p>
                <hr style="margin: 24px 0; border: none; border-top: 1px solid #e2e8f0;">
                <p style="color: #64748b; font-size: 13px;">Didn't create this account? You can safely ignore this email.</p>
                <p style="color: #0f172a; font-size: 14px; margin-top: 16px;"><strong>— The ZetsuServ Team</strong><br>
                <span style="color:#64748b;">Support: support@zetsuserv.com</span></p>
            </div>
        </div>
        """
        msg.body = (
            f"ZetsuServ Team — Email Verification\n\n"
            f"Hi {user.full_name or user.username},\n\n"
            f"Enter this 6-digit code to activate your account: {spaced_code}\n"
            f"This code expires in 10 minutes. Do not share it with anyone.\n\n"
            f"Open the verification page: {verification_url}\n\n"
            f"— The ZetsuServ Team\nSupport: support@zetsuserv.com\n"
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send verification email: {e}')
