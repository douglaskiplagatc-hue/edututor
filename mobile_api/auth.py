from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity, get_jwt
)
from app import db
from app.models import User, Tutor
from app.validators import validate_email, validate_phone
from app.notifications import PushNotificationService
import jwt
import datetime
import hashlib

mobile_auth = Blueprint('mobile_auth', __name__)

# Token blocklist for logout
token_blocklist = set()

@mobile_auth.route('/register', methods=['POST'])
def mobile_register():
    """Mobile user registration"""
    data = request.get_json()
    
    # Validation
    required_fields = ['email', 'phone', 'password', 'user_type', 'username']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': f'Missing required field: {field}'
            }), 400
    
    # Validate email
    if not validate_email(data['email']):
        return jsonify({
            'success': False,
            'error': 'Invalid email address'
        }), 400
    
    # Validate phone (Kenyan format)
    if not validate_phone(data['phone']):
        return jsonify({
            'success': False,
            'error': 'Invalid phone number. Use format: 0712 345 678'
        }), 400
    
    # Check if user exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'success': False,
            'error': 'Email already registered'
        }), 409
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({
            'success': False,
            'error': 'Username already taken'
        }), 409
    
    # Create user
    user = User(
        username=data['username'],
        email=data['email'],
        phone=data['phone'],
        location=data.get('location', 'Nairobi'),
        user_type=data['user_type']
    )
    user.set_password(data['password'])
    
    # Device token for push notifications
    device_token = data.get('device_token')
    if device_token:
        user.device_token = device_token
    
    db.session.add(user)
    db.session.commit()
    
    # If registering as tutor, create tutor profile
    if data['user_type'] == 'tutor':
        tutor = Tutor(
            user_id=user.id,
            full_name=data.get('full_name', user.username),
            qualifications=data.get('qualifications', ''),
            subjects=data.get('subjects', ''),
            hourly_rate=data.get('hourly_rate', 500),
            level=data.get('level', 'secondary'),
            experience_years=data.get('experience_years', 0),
            teaching_mode=data.get('teaching_mode', 'both')
        )
        db.session.add(tutor)
        db.session.commit()
    
    # Generate JWT tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    # Send welcome notification
    PushNotificationService.send_fcm_notification(
        device_token,
        'Welcome to EduTutor Kenya! 🎓',
        f'Hi {user.username}, your account has been created successfully!'
    )
    
    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'user_type': user.user_type,
            'profile_picture': user.profile_picture,
            'is_verified': user.is_verified
        },
        'tokens': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': 3600  # 1 hour
        }
    }), 201

@mobile_auth.route('/login', methods=['POST'])
def mobile_login():
    """Mobile user login"""
    data = request.get_json()
    
    # Accept email or username
    identifier = data.get('email') or data.get('username')
    password = data.get('password')
    device_token = data.get('device_token')
    
    if not identifier or not password:
        return jsonify({
            'success': False,
            'error': 'Email/username and password required'
        }), 400
    
    # Find user by email or username
    user = User.query.filter(
        (User.email == identifier) | (User.username == identifier)
    ).first()
    
    if not user or not user.check_password(password):
        return jsonify({
            'success': False,
            'error': 'Invalid credentials'
        }), 401
    
    if not user.is_active:
        return jsonify({
            'success': False,
            'error': 'Account is deactivated'
        }), 403
    
    # Update device token
    if device_token and device_token != user.device_token:
        user.device_token = device_token
        db.session.commit()
    
    # Update last login
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()
    
    # Generate tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    # Get tutor info if applicable
    tutor_info = None
    if user.user_type == 'tutor':
        tutor = Tutor.query.filter_by(user_id=user.id).first()
        if tutor:
            tutor_info = {
                'tutor_id': tutor.id,
                'full_name': tutor.full_name,
                'rating': tutor.rating,
                'subjects': tutor.subjects,
                'hourly_rate': tutor.hourly_rate,
                'is_verified': tutor.is_verified
            }
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'user_type': user.user_type,
            'profile_picture': user.profile_picture,
            'location': user.location,
            'is_verified': user.is_verified
        },
        'tutor_info': tutor_info,
        'tokens': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': 3600
        }
    })

@mobile_auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """Refresh access token"""
    current_user_id = get_jwt_identity()
    
    # Check if user exists and is active
    user = User.query.get(current_user_id)
    if not user or not user.is_active:
        return jsonify({
            'success': False,
            'error': 'User not found or inactive'
        }), 401
    
    new_access_token = create_access_token(identity=current_user_id)
    
    return jsonify({
        'success': True,
        'access_token': new_access_token,
        'token_type': 'bearer',
        'expires_in': 3600
    })

@mobile_auth.route('/logout', methods=['POST'])
@jwt_required()
def mobile_logout():
    """Mobile user logout"""
    jti = get_jwt()['jti']
    token_blocklist.add(jti)
    
    # Clear device token
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user:
        user.device_token = None
        db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

@mobile_auth.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({
            'success': False,
            'error': 'Email is required'
        }), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal if user exists for security
        return jsonify({
            'success': True,
            'message': 'If the email exists, you will receive reset instructions'
        })
    
    # Generate reset token (valid for 1 hour)
    reset_token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        'type': 'password_reset'
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    # Save reset token to user
    user.reset_token = reset_token
    user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    db.session.commit()
    
    # Send reset email
    reset_link = f"{current_app.config['MOBILE_APP_URL']}/reset-password?token={reset_token}"
    
    PushNotificationService.send_email_notification(
        user.email,
        'Password Reset Request',
        'password_reset',
        {
            'user_name': user.username,
            'reset_link': reset_link,
            'expiry_hours': 1
        }
    )
    
    # Also send SMS if enabled
    PushNotificationService.send_sms_notification(
        user.phone,
        f'EduTutor Kenya: Password reset requested. Use token: {reset_token[:6]}...'
    )
    
    return jsonify({
        'success': True,
        'message': 'Password reset instructions sent'
    })

@mobile_auth.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({
            'success': False,
            'error': 'Token and new password are required'
        }), 400
    
    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 6 characters'
        }), 400
    
    try:
        # Verify token
        payload = jwt.decode(
            token, 
            current_app.config['SECRET_KEY'], 
            algorithms=['HS256']
        )
        
        if payload.get('type') != 'password_reset':
            return jsonify({
                'success': False,
                'error': 'Invalid token type'
            }), 400
        
        user_id = payload.get('user_id')
        user = User.query.get(user_id)
        
        if not user or user.reset_token != token:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token'
            }), 400
        
        if user.reset_token_expiry < datetime.datetime.utcnow():
            return jsonify({
                'success': False,
                'error': 'Token has expired'
            }), 400
        
        # Update password
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        # Send confirmation
        PushNotificationService.send_fcm_notification(
            user.device_token,
            'Password Changed',
            'Your password has been changed successfully'
        )
        
        return jsonify({
            'success': True,
            'message': 'Password reset successful'
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({
            'success': False,
            'error': 'Token has expired'
        }), 400
    except jwt.InvalidTokenError:
        return jsonify({
            'success': False,
            'error': 'Invalid token'
        }), 400

@mobile_auth.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    # Get tutor info if applicable
    tutor_info = None
    if user.user_type == 'tutor':
        tutor = Tutor.query.filter_by(user_id=user.id).first()
        if tutor:
            tutor_info = {
                'id': tutor.id,
                'full_name': tutor.full_name,
                'qualifications': tutor.qualifications,
                'subjects': tutor.subjects,
                'level': tutor.level,
                'experience_years': tutor.experience_years,
                'hourly_rate': tutor.hourly_rate,
                'availability': tutor.availability,
                'teaching_mode': tutor.teaching_mode,
                'bio': tutor.bio,
                'rating': tutor.rating,
                'review_count': tutor.review_count,
                'completed_sessions': tutor.completed_sessions,
                'is_verified': tutor.is_verified,
                'is_featured': tutor.is_featured
            }
    
    return jsonify({
        'success': True,
        'profile': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'location': user.location,
            'user_type': user.user_type,
            'profile_picture': user.profile_picture,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'is_active': user.is_active,
            'is_verified': user.is_verified
        },
        'tutor_info': tutor_info
    })

@mobile_auth.route('/profile/update', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    data = request.get_json()
    
    # Update allowed fields
    allowed_fields = ['username', 'phone', 'location', 'profile_picture']
    for field in allowed_fields:
        if field in data:
            setattr(user, field, data[field])
    
    # Special handling for profile picture (base64)
    if 'profile_picture_base64' in data:
        from app.utils import save_base64_image
        filename = save_base64_image(data['profile_picture_base64'], user.id)
        if filename:
            user.profile_picture = filename
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully',
        'profile': {
            'username': user.username,
            'phone': user.phone,
            'location': user.location,
            'profile_picture': user.profile_picture
        }
    })

@mobile_auth.route('/update-device-token', methods=['POST'])
@jwt_required()
def update_device_token():
    """Update device token for push notifications"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    device_token = data.get('device_token')
    if not device_token:
        return jsonify({
            'success': False,
            'error': 'Device token is required'
        }), 400
    
    user = User.query.get(user_id)
    if user:
        user.device_token = device_token
        db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Device token updated'
    })