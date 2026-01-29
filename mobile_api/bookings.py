from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import Booking, Tutor, User, Payment
from app.mpesa import MpesaService
from app.video import VideoMeetingService
from app.notifications import PushNotificationService
import uuid

mobile_bookings = Blueprint('mobile_bookings', __name__)

@mobile_bookings.route('/create', methods=['POST'])
@jwt_required()
def create_booking():
    """Create a new booking"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['tutor_id', 'subject', 'hours', 'schedule_date', 'schedule_time']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': f'Missing required field: {field}'
            }), 400
    
    # Check if tutor exists and is available
    tutor = Tutor.query.get(data['tutor_id'])
    if not tutor:
        return jsonify({
            'success': False,
            'error': 'Tutor not found'
        }), 404
    
    if not tutor.is_available:
        return jsonify({
            'success': False,
            'error': 'Tutor is not currently accepting bookings'
        }), 400
    
    # Check if tutor is verified
    if not tutor.is_verified:
        return jsonify({
            'success': False,
            'error': 'Tutor is not verified'
        }), 400
    
    # Parse date
    try:
        schedule_date = datetime.strptime(data['schedule_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400
    
    # Check if date is in the future
    if schedule_date < datetime.utcnow().date():
        return jsonify({
            'success': False,
            'error': 'Cannot book sessions in the past'
        }), 400
    
    # Calculate total amount
    hours = int(data['hours'])
    total_amount = tutor.hourly_rate * hours
    
    # Platform fee (15%)
    platform_fee = total_amount * 0.15
    tutor_payout = total_amount - platform_fee
    
    # Create booking
    booking = Booking(
        student_id=user_id,
        tutor_id=tutor.id,
        subject=data['subject'],
        hours=hours,
        total_amount=total_amount,
        platform_fee=platform_fee,
        tutor_payout=tutor_payout,
        location=data.get('location'),
        schedule_date=schedule_date,
        schedule_time=data['schedule_time'],
        notes=data.get('notes', ''),
        status='pending',
        payment_status='pending',
        booking_type=data.get('booking_type', 'regular')  # regular, quick, package
    )
    
    db.session.add(booking)
    db.session.commit()
    
    # Send notification to tutor
    student = User.query.get(user_id)
    PushNotificationService.send_fcm_notification(
        tutor.user.device_token,
        'New Booking Request 📚',
        f'{student.username} wants to book a {data["subject"]} session',
        {
            'type': 'new_booking',
            'booking_id': booking.id,
            'student_name': student.username,
            'subject': data['subject'],
            'amount': total_amount
        }
    )
    
    # Send email notification
    PushNotificationService.send_email_notification(
        tutor.user.email,
        'New Booking Request - EduTutor Kenya',
        'new_booking_tutor',
        {
            'tutor_name': tutor.full_name,
            'student_name': student.username,
            'subject': data['subject'],
            'date': schedule_date.strftime('%B %d, %Y'),
            'time': data['schedule_time'],
            'hours': hours,
            'amount': total_amount,
            'booking_id': booking.id
        }
    )
    
    return jsonify({
        'success': True,
        'message': 'Booking request sent successfully',
        'booking': {
            'id': booking.id,
            'tutor_name': tutor.full_name,
            'subject': booking.subject,
            'hours': booking.hours,
            'total_amount': booking.total_amount,
            'schedule_date': booking.schedule_date.isoformat(),
            'schedule_time': booking.schedule_time,
            'status': booking.status,
            'created_at': booking.created_at.isoformat()
        },
        'next_steps': {
            'payment_required': True,
            'payment_amount': total_amount,
            'tutor_confirmation': 'Waiting for tutor to confirm availability'
        }
    }), 201

@mobile_bookings.route('/list', methods=['GET'])
@jwt_required()
def list_bookings():
    """Get user's bookings with filters"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Get query parameters
    status = request.args.get('status')
    booking_type = request.args.get('type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query based on user type
    if user.user_type == 'student':
        bookings_query = Booking.query.filter_by(student_id=user_id)
    else:  # tutor
        tutor = Tutor.query.filter_by(user_id=user_id).first()
        if not tutor:
            return jsonify({
                'success': False,
                'error': 'Tutor profile not found'
            }), 404
        bookings_query = Booking.query.filter_by(tutor_id=tutor.id)
    
    # Apply filters
    if status:
        bookings_query = bookings_query.filter_by(status=status)
    
    if booking_type:
        bookings_query = bookings_query.filter_by(booking_type=booking_type)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            bookings_query = bookings_query.filter(Booking.schedule_date >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            bookings_query = bookings_query.filter(Booking.schedule_date <= date_to_obj)
        except ValueError:
            pass
    
    # Get total count
    total = bookings_query.count()
    
    # Get bookings with pagination
    bookings = bookings_query.order_by(Booking.created_at.desc())\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    
    bookings_list = []
    for booking in bookings:
        # Get tutor/student info
        if user.user_type == 'student':
            other_party = booking.tutor
            other_party_type = 'tutor'
        else:
            other_party = booking.student
            other_party_type = 'student'
        
        bookings_list.append({
            'id': booking.id,
            'subject': booking.subject,
            'hours': booking.hours,
            'total_amount': booking.total_amount,
            'schedule_date': booking.schedule_date.isoformat(),
            'schedule_time': booking.schedule_time,
            'status': booking.status,
            'payment_status': booking.payment_status,
            'booking_type': booking.booking_type,
            'created_at': booking.created_at.isoformat(),
            'other_party': {
                'id': other_party.id if other_party_type == 'tutor' else other_party.id,
                'name': other_party.full_name if other_party_type == 'tutor' else other_party.username,
                'type': other_party_type,
                'profile_picture': other_party.user.profile_picture if other_party_type == 'tutor' else other_party.profile_picture
            },
            'has_video': booking.video_meeting_id is not None,
            'can_join': can_join_session(booking),
            'actions': get_available_actions(booking, user.user_type)
        })
    
    return jsonify({
        'success': True,
        'bookings': bookings_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        },
        'filters': {
            'status': status,
            'type': booking_type,
            'date_from': date_from,
            'date_to': date_to
        }
    })

@mobile_bookings.route('/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_booking_detail(booking_id):
    """Get detailed booking information"""
    user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    
    # Check authorization
    if booking.student_id != user_id and booking.tutor.user_id != user_id:
        return jsonify({
            'success': False,
            'error': 'Unauthorized to view this booking'
        }), 403
    
    # Get payment info
    payment = Payment.query.filter_by(booking_id=booking_id).first()
    
    # Get video meeting info if exists
    video_info = None
    if booking.video_meeting_id:
        video_info = {
            'meeting_id': booking.video_meeting_id,
            'provider': booking.video_provider,
            'join_url': booking.video_join_url,
            'start_url': booking.video_start_url if booking.tutor.user_id == user_id else None,
            'password': booking.video_password
        }
    
    # Get messages count
    from app.models import Message
    message_count = Message.query.filter_by(booking_id=booking_id).count()
    
    booking_detail = {
        'id': booking.id,
        'subject': booking.subject,
        'hours': booking.hours,
        'total_amount': booking.total_amount,
        'platform_fee': booking.platform_fee,
        'tutor_payout': booking.tutor_payout,
        'location': booking.location,
        'schedule_date': booking.schedule_date.isoformat(),
        'schedule_time': booking.schedule_time,
        'notes': booking.notes,
        'status': booking.status,
        'payment_status': booking.payment_status,
        'booking_type': booking.booking_type,
        'created_at': booking.created_at.isoformat(),
        'updated_at': booking.updated_at.isoformat() if booking.updated_at else None,
        'student': {
            'id': booking.student.id,
            'name': booking.student.username,
            'email': booking.student.email,
            'phone': booking.student.phone,
            'profile_picture': booking.student.profile_picture
        },
        'tutor': {
            'id': booking.tutor.id,
            'name': booking.tutor.full_name,
            'email': booking.tutor.user.email,
            'phone': booking.tutor.user.phone,
            'profile_picture': booking.tutor.user.profile_picture,
            'rating': booking.tutor.rating,
            'subjects': booking.tutor.subjects
        },
        'payment': {
            'status': payment.status if payment else 'pending',
            'mpesa_receipt': payment.mpesa_receipt if payment else None,
            'phone_number': payment.phone_number if payment else None,
            'transaction_date': payment.transaction_date.isoformat() if payment and payment.transaction_date else None
        } if payment else None,
        'video': video_info,
        'chat': {
            'message_count': message_count,
            'unread_count': Message.query.filter_by(
                booking_id=booking_id,
                receiver_id=user_id,
                is_read=False
            ).count()
        },
        'timeline': get_booking_timeline(booking),
        'actions': get_available_actions(booking, booking.student_id == user_id and 'student' or 'tutor')
    }
    
    return jsonify({
        'success': True,
        'booking': booking_detail
    })

@mobile_bookings.route('/<int:booking_id>/confirm', methods=['POST'])
@jwt_required()
def confirm_booking(booking_id):
    """Tutor confirms booking"""
    user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user is the tutor
    tutor = Tutor.query.filter_by(user_id=user_id).first()
    if not tutor or booking.tutor_id != tutor.id:
        return jsonify({
            'success': False,
            'error': 'Only the assigned tutor can confirm bookings'
        }), 403
    
    # Check if booking can be confirmed
    if booking.status != 'pending':
        return jsonify({
            'success': False,
            'error': f'Booking is already {booking.status}'
        }), 400
    
    # Update booking status
    booking.status = 'confirmed'
    booking.confirmed_at = datetime.utcnow()
    db.session.commit()
    
    # Send notification to student
    PushNotificationService.send_fcm_notification(
        booking.student.device_token,
        'Booking Confirmed! ✅',
        f'{tutor.full_name} has confirmed your {booking.subject} session',
        {
            'type': 'booking_confirmed',
            'booking_id': booking.id,
            'tutor_name': tutor.full_name,
            'subject': booking.subject
        }
    )
    
    # Send email
    PushNotificationService.send_email_notification(
        booking.student.email,
        'Booking Confirmed - EduTutor Kenya',
        'booking_confirmed_student',
        {
            'student_name': booking.student.username,
            'tutor_name': tutor.full_name,
            'subject': booking.subject,
            'date': booking.schedule_date.strftime('%B %d, %Y'),
            'time': booking.schedule_time,
            'hours': booking.hours,
            'amount': booking.total_amount,
            'booking_id': booking.id
        }
    )
    
    return jsonify({
        'success': True,
        'message': 'Booking confirmed successfully',
        'booking': {
            'id': booking.id,
            'status': booking.status,
            'confirmed_at': booking.confirmed_at.isoformat()
        }
    })

@mobile_bookings.route('/<int:booking_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    """Cancel a booking"""
    user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    data = request.get_json()
    
    # Check authorization
    is_student = booking.student_id == user_id
    is_tutor = booking.tutor.user_id == user_id
    
    if not (is_student or is_tutor):
        return jsonify({
            'success': False,
            'error': 'Unauthorized to cancel this booking'
        }), 403
    
    # Check if booking can be cancelled
    if booking.status in ['cancelled', 'completed']:
        return jsonify({
            'success': False,
            'error': f'Cannot cancel a {booking.status} booking'
        }), 400
    
    # Check cancellation policy (24 hours before session)
    session_datetime = datetime.combine(booking.schedule_date, datetime.strptime(booking.schedule_time, '%H:%M').time())
    time_until_session = session_datetime - datetime.utcnow()
    
    if time_until_session < timedelta(hours=24) and is_student:
        return jsonify({
            'success': False,
            'error': 'Cancellations must be made at least 24 hours before the session'
        }), 400
    
    # Update booking
    booking.status = 'cancelled'
    booking.cancelled_at = datetime.utcnow()
    booking.cancellation_reason = data.get('reason', '')
    booking.cancelled_by = 'student' if is_student else 'tutor'
    
    # Refund if paid
    payment = Payment.query.filter_by(booking_id=booking_id, status='completed').first()
    if payment and is_student:
        booking.refund_status = 'pending'
        booking.refund_amount = booking.total_amount
        
        # Initiate refund process (would integrate with M-Pesa B2C)
        # For now, mark for manual processing
        booking.refund_notes = 'Refund to be processed manually'
    
    db.session.commit()
    
    # Notify the other party
    if is_student:
        other_party = booking.tutor.user
        cancelled_by = booking.student.username
    else:
        other_party = booking.student
        cancelled_by = booking.tutor.full_name
    
    PushNotificationService.send_fcm_notification(
        other_party.device_token,
        'Booking Cancelled ❌',
        f'{cancelled_by} has cancelled the {booking.subject} session',
        {
            'type': 'booking_cancelled',
            'booking_id': booking.id,
            'cancelled_by': cancelled_by,
            'reason': booking.cancellation_reason
        }
    )
    
    return jsonify({
        'success': True,
        'message': 'Booking cancelled successfully',
        'refund_info': {
            'eligible': payment is not None and is_student,
            'status': booking.refund_status,
            'amount': booking.refund_amount
        } if is_student else None
    })

@mobile_bookings.route('/<int:booking_id>/complete', methods=['POST'])
@jwt_required()
def complete_booking(booking_id):
    """Mark booking as completed"""
    user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if user is the student or tutor
    is_student = booking.student_id == user_id
    is_tutor = booking.tutor.user_id == user_id
    
    if not (is_student or is_tutor):
        return jsonify({
            'success': False,
            'error': 'Unauthorized to complete this booking'
        }), 403
    
    # Check if booking can be completed
    if booking.status != 'confirmed':
        return jsonify({
            'success': False,
            'error': f'Cannot complete a {booking.status} booking'
        }), 400
    
    # Check if session time has passed
    session_datetime = datetime.combine(booking.schedule_date, datetime.strptime(booking.schedule_time, '%H:%M').time())
    if datetime.utcnow() < session_datetime:
        return jsonify({
            'success': False,
            'error': 'Cannot complete booking before scheduled session time'
        }), 400
    
    # Update booking
    booking.status = 'completed'
    booking.completed_at = datetime.utcnow()
    
    # Update tutor stats
    booking.tutor.completed_sessions += 1
    
    # Release payment to tutor (after 24-hour review period)
    booking.tutor_payout_released = False
    booking.tutor_payout_scheduled = datetime.utcnow() + timedelta(hours=24)
    
    db.session.commit()
    
    # Send completion notifications
    if is_student:
        other_party = booking.tutor.user
        completed_by = booking.student.username
    else:
        other_party = booking.student
        completed_by = booking.tutor.full_name
    
    PushNotificationService.send_fcm_notification(
        other_party.device_token,
        'Session Completed 🎓',
        f'{completed_by} marked the {booking.subject} session as complete',
        {
            'type': 'booking_completed',
            'booking_id': booking.id,
            'completed_by': completed_by
        }
    )
    
    # Request review from student
    if is_tutor:
        PushNotificationService.send_fcm_notification(
            booking.student.device_token,
            'Rate Your Session ⭐',
            f'How was your {booking.subject} session with {booking.tutor.full_name}?',
            {
                'type': 'request_review',
                'booking_id': booking.id,
                'tutor_name': booking.tutor.full_name,
                'subject': booking.subject
            }
        )
    
    return jsonify({
        'success': True,
        'message': 'Booking marked as completed',
        'booking': {
            'id': booking.id,
            'status': booking.status,
            'completed_at': booking.completed_at.isoformat()
        },
        'next_steps': {
            'review_requested': is_tutor,
            'payout_scheduled': booking.tutor_payout_scheduled.isoformat()
        }
    })

@mobile_bookings.route('/<int:booking_id>/video/create', methods=['POST'])
@jwt_required()
def create_video_meeting(booking_id):
    """Create video meeting for booking"""
    user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    
    # Check authorization (only tutor can create meetings)
    tutor = Tutor.query.filter_by(user_id=user_id).first()
    if not tutor or booking.tutor_id != tutor.id:
        return jsonify({
            'success': False,
            'error': 'Only the tutor can create video meetings'
        }), 403
    
    # Check if booking is confirmed
    if booking.status != 'confirmed':
        return jsonify({
            'success': False,
            'error': 'Cannot create meeting for unconfirmed booking'
        }), 400
    
    # Check if meeting already exists
    if booking.video_meeting_id:
        return jsonify({
            'success': False,
            'error': 'Video meeting already exists for this booking'
        }), 400
    
    data = request.get_json()
    provider = data.get('provider', 'zoom')
    
    # Calculate meeting time
    meeting_time = datetime.combine(
        booking.schedule_date,
        datetime.strptime(booking.schedule_time, '%H:%M').time()
    )
    
    # Create meeting
    video_service = VideoMeetingService()
    meeting = video_service.create_meeting(
        provider=provider,
        topic=f'{booking.subject} - {booking.student.username} & {tutor.full_name}',
        duration=booking.hours * 60,
        start_time=meeting_time,
        host_email=tutor.user.email
    )
    
    if not meeting:
        return jsonify({
            'success': False,
            'error': 'Failed to create video meeting'
        }), 500
    
    # Update booking with meeting info
    booking.video_provider = provider
    booking.video_meeting_id = meeting.get('meeting_id') or meeting.get('room_name')
    booking.video_join_url = meeting.get('join_url') or meeting.get('room_url')
    booking.video_start_url = meeting.get('start_url')
    booking.video_password = meeting.get('password')
    
    db.session.commit()
    
    # Send notification to student
    PushNotificationService.send_fcm_notification(
        booking.student.device_token,
        'Video Meeting Created 🎥',
        f'{tutor.full_name} has created a video meeting for your {booking.subject} session',
        {
            'type': 'video_meeting_created',
            'booking_id': booking.id,
            'tutor_name': tutor.full_name,
            'join_url': booking.video_join_url
        }
    )
    
    return jsonify({
        'success': True,
        'message': 'Video meeting created successfully',
        'meeting': {
            'provider': provider,
            'meeting_id': booking.video_meeting_id,
            'join_url': booking.video_join_url,
            'start_url': booking.video_start_url if booking.tutor.user_id == user_id else None,
            'password': booking.video_password,
            'meeting_time': meeting_time.isoformat()
        }
    })

# Helper functions
def can_join_session(booking):
    """Check if user can join the video session"""
    if not booking.video_join_url:
        return False
    
    # Check if session time is within reasonable window
    session_datetime = datetime.combine(
        booking.schedule_date,
        datetime.strptime(booking.schedule_time, '%H:%M').time()
    )
    
    now = datetime.utcnow()
    time_diff = (now - session_datetime).total_seconds() / 3600  # hours
    
    # Allow joining 15 minutes before to 2 hours after scheduled time
    return -0.25 <= time_diff <= 2.0

def get_available_actions(booking, user_type):
    """Get available actions for booking based on user type and status"""
    actions = []
    
    if user_type == 'student':
        if booking.status == 'pending' and booking.payment_status == 'pending':
            actions.append('pay')
        if booking.status == 'pending':
            actions.append('cancel')
        if booking.status == 'confirmed' and can_join_session(booking):
            actions.append('join_video')
        if booking.status == 'confirmed' and not can_join_session(booking):
            actions.append('reschedule')
        if booking.status == 'completed' and not booking.is_reviewed:
            actions.append('review')
    
    else:  # tutor
        if booking.status == 'pending':
            actions.append('confirm')
            actions.append('reject')
        if booking.status == 'confirmed':
            actions.append('create_video')
        if booking.status == 'confirmed' and can_join_session(booking):
            actions.append('join_video')
        if booking.status == 'confirmed':
            actions.append('cancel')
        if booking.status == 'completed' and not booking.tutor_payout_released:
            actions.append('request_payout')
    
    return actions

def get_booking_timeline(booking):
    """Get timeline of booking events"""
    timeline = []
    
    # Created
    timeline.append({
        'event': 'booking_created',
        'timestamp': booking.created_at.isoformat(),
        'description': 'Booking request sent',
        'user': booking.student.username
    })
    
    # Confirmed
    if booking.confirmed_at:
        timeline.append({
            'event': 'booking_confirmed',
            'timestamp': booking.confirmed_at.isoformat(),
            'description': 'Booking confirmed by tutor',
            'user': booking.tutor.full_name
        })
    
    # Payment
    payment = Payment.query.filter_by(booking_id=booking.id).first()
    if payment and payment.completed_at:
        timeline.append({
            'event': 'payment_completed',
            'timestamp': payment.completed_at.isoformat(),
            'description': f'Payment of KES {booking.total_amount} completed',
            'details': {
                'mpesa_receipt': payment.mpesa_receipt,
                'phone': payment.phone_number
            }
        })
    
    # Video meeting created
    if booking.video_meeting_created_at:
        timeline.append({
            'event': 'video_meeting_created',
            'timestamp': booking.video_meeting_created_at.isoformat(),
            'description': 'Video meeting created',
            'user': booking.tutor.full_name
        })
    
    # Completed
    if booking.completed_at:
        timeline.append({
            'event': 'booking_completed',
            'timestamp': booking.completed_at.isoformat(),
            'description': 'Session marked as completed'
        })
    
    # Cancelled
    if booking.cancelled_at:
        timeline.append({
            'event': 'booking_cancelled',
            'timestamp': booking.cancelled_at.isoformat(),
            'description': f'Booking cancelled by {booking.cancelled_by}',
            'reason': booking.cancellation_reason
        })
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x['timestamp'])
    return timeline