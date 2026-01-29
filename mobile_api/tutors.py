from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from app import db
from app.models import Tutor, User, Review, Booking
from app.recommendation import RecommendationEngine
from math import radians, sin, cos, sqrt, atan2
import json

mobile_tutors = Blueprint('mobile_tutors', __name__)

@mobile_tutors.route('/search', methods=['GET'])
def search_tutors():
    """Search tutors with filters"""
    # Get query parameters
    query = request.args.get('q', '')
    location = request.args.get('location', '')
    subject = request.args.get('subject', '')
    level = request.args.get('level', '')
    min_rate = request.args.get('min_rate', type=float)
    max_rate = request.args.get('max_rate', type=float)
    min_rating = request.args.get('min_rating', type=float)
    teaching_mode = request.args.get('teaching_mode', '')
    availability = request.args.get('availability', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get user location for distance calculation
    user_lat = request.args.get('lat', type=float)
    user_lng = request.args.get('lng', type=float)
    max_distance = request.args.get('max_distance', 50, type=float)  # km
    
    # Start query
    tutors_query = Tutor.query.filter_by(is_verified=True, is_available=True)
    
    # Apply filters
    if query:
        tutors_query = tutors_query.filter(
            or_(
                Tutor.full_name.ilike(f'%{query}%'),
                Tutor.subjects.ilike(f'%{query}%'),
                Tutor.qualifications.ilike(f'%{query}%')
            )
        )
    
    if location:
        tutors_query = tutors_query.join(User).filter(
            User.location.ilike(f'%{location}%')
        )
    
    if subject:
        tutors_query = tutors_query.filter(
            Tutor.subjects.ilike(f'%{subject}%')
        )
    
    if level:
        tutors_query = tutors_query.filter_by(level=level)
    
    if min_rate:
        tutors_query = tutors_query.filter(Tutor.hourly_rate >= min_rate)
    
    if max_rate:
        tutors_query = tutors_query.filter(Tutor.hourly_rate <= max_rate)
    
    if min_rating:
        tutors_query = tutors_query.filter(Tutor.rating >= min_rating)
    
    if teaching_mode:
        tutors_query = tutors_query.filter_by(teaching_mode=teaching_mode)
    
    if availability:
        tutors_query = tutors_query.filter(
            Tutor.availability.ilike(f'%{availability}%')
        )
    
    # Get total count before pagination
    total = tutors_query.count()
    
    # Apply pagination
    tutors = tutors_query.order_by(Tutor.rating.desc())\
        .offset((page - 1) * per_page)\
        .limit(per_page)\
        .all()
    
    # Format response
    tutors_list = []
    for tutor in tutors:
        # Calculate distance if user location provided
        distance = None
        if user_lat and user_lng:
            # Mock distance calculation (in real app, use tutor's lat/lng)
            distance = calculate_distance(
                user_lat, user_lng,
                -1.286389, 36.817223  # Nairobi coordinates (mock)
            )
        
        # Only include if within max distance
        if distance and distance > max_distance:
            continue
        
        tutors_list.append({
            'id': tutor.id,
            'full_name': tutor.full_name,
            'profile_picture': tutor.user.profile_picture,
            'subjects': tutor.subjects,
            'level': tutor.level,
            'rating': tutor.rating,
            'review_count': tutor.review_count,
            'experience_years': tutor.experience_years,
            'hourly_rate': tutor.hourly_rate,
            'availability': tutor.availability,
            'teaching_mode': tutor.teaching_mode,
            'location': tutor.user.location,
            'distance': distance,
            'is_featured': tutor.is_featured,
            'is_available': tutor.is_available,
            'bio_preview': tutor.bio[:100] + '...' if len(tutor.bio) > 100 else tutor.bio
        })
    
    return jsonify({
        'success': True,
        'tutors': tutors_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        }
    })

@mobile_tutors.route('/<int:tutor_id>', methods=['GET'])
def get_tutor_detail(tutor_id):
    """Get detailed tutor information"""
    tutor = Tutor.query.get_or_404(tutor_id)
    
    # Get reviews
    reviews = Review.query.filter_by(tutor_id=tutor_id)\
        .order_by(Review.created_at.desc())\
        .limit(10)\
        .all()
    
    # Get availability schedule
    from app.models import Schedule
    schedule = Schedule.query.filter_by(tutor_id=tutor_id).all()
    
    # Get tutor's recent bookings
    recent_bookings = Booking.query.filter_by(tutor_id=tutor_id)\
        .order_by(Booking.created_at.desc())\
        .limit(5)\
        .all()
    
    reviews_list = []
    for review in reviews:
        reviews_list.append({
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
            'student_name': review.author.username,
            'date': review.created_at.strftime('%Y-%m-%d'),
            'subject': review.booking.subject if review.booking else 'General'
        })
    
    schedule_list = []
    for slot in schedule:
        schedule_list.append({
            'day': slot.get_day_name(),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M'),
            'is_available': slot.is_available
        })
    
    return jsonify({
        'success': True,
        'tutor': {
            'id': tutor.id,
            'full_name': tutor.full_name,
            'profile_picture': tutor.user.profile_picture,
            'email': tutor.user.email,
            'phone': tutor.user.phone,
            'location': tutor.user.location,
            'subjects': tutor.subjects.split(','),
            'level': tutor.level,
            'qualifications': tutor.qualifications,
            'experience_years': tutor.experience_years,
            'hourly_rate': tutor.hourly_rate,
            'availability': tutor.availability,
            'teaching_mode': tutor.teaching_mode,
            'bio': tutor.bio,
            'rating': tutor.rating,
            'review_count': tutor.review_count,
            'completed_sessions': tutor.completed_sessions,
            'is_verified': tutor.is_verified,
            'is_featured': tutor.is_featured,
            'is_available': tutor.is_available,
            'response_rate': 95,  # Mock data
            'response_time': 'Within 2 hours',
            'cancellation_rate': 5  # Mock data
        },
        'reviews': reviews_list,
        'schedule': schedule_list,
        'statistics': {
            'total_students': len(set([b.student_id for b in recent_bookings])),
            'repeat_rate': 65,  # Mock data
            'subject_expertise': get_subject_expertise(tutor_id)
        }
    })

@mobile_tutors.route('/recommended', methods=['GET'])
@jwt_required()
def recommended_tutors():
    """Get recommended tutors for logged-in user"""
    user_id = get_jwt_identity()
    
    recommendation_engine = RecommendationEngine()
    recommended = recommendation_engine.recommend_tutors_for_student(user_id, limit=10)
    
    tutors_list = []
    for tutor in recommended:
        tutors_list.append({
            'id': tutor.id,
            'full_name': tutor.full_name,
            'profile_picture': tutor.user.profile_picture,
            'subjects': tutor.subjects,
            'rating': tutor.rating,
            'hourly_rate': tutor.hourly_rate,
            'location': tutor.user.location,
            'match_score': 85,  # Mock match score
            'reason': 'Based on your search history'  # Mock reason
        })
    
    return jsonify({
        'success': True,
        'tutors': tutors_list,
        'recommendation_count': len(tutors_list)
    })

@mobile_tutors.route('/nearby', methods=['GET'])
def nearby_tutors():
    """Get tutors near user location"""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', 10, type=float)  # km
    
    if not lat or not lng:
        return jsonify({
            'success': False,
            'error': 'Latitude and longitude are required'
        }), 400
    
    # In production, this would query tutors with geolocation data
    # For now, return mock data
    tutors = Tutor.query.filter_by(is_verified=True, is_available=True)\
        .order_by(Tutor.rating.desc())\
        .limit(20)\
        .all()
    
    tutors_list = []
    for tutor in tutors:
        # Mock distance calculation
        distance = calculate_distance(
            lat, lng,
            -1.286389, 36.817223  # Nairobi coordinates
        )
        
        if distance <= radius:
            tutors_list.append({
                'id': tutor.id,
                'full_name': tutor.full_name,
                'profile_picture': tutor.user.profile_picture,
                'subjects': tutor.subjects,
                'rating': tutor.rating,
                'hourly_rate': tutor.hourly_rate,
                'distance': round(distance, 1),
                'location': tutor.user.location,
                'available_now': check_tutor_availability(tutor.id)
            })
    
    # Sort by distance
    tutors_list.sort(key=lambda x: x['distance'])
    
    return jsonify({
        'success': True,
        'tutors': tutors_list[:10],  # Top 10 nearest
        'user_location': {
            'lat': lat,
            'lng': lng,
            'radius': radius
        }
    })

@mobile_tutors.route('/<int:tutor_id>/availability', methods=['GET'])
def check_availability(tutor_id):
    """Check tutor's availability for specific date/time"""
    date_str = request.args.get('date')
    time_str = request.args.get('time')
    
    if not date_str or not time_str:
        return jsonify({
            'success': False,
            'error': 'Date and time are required'
        }), 400
    
    tutor = Tutor.query.get_or_404(tutor_id)
    
    # Check if tutor is available
    if not tutor.is_available:
        return jsonify({
            'success': True,
            'available': False,
            'reason': 'Tutor is not currently accepting bookings'
        })
    
    # Check if time slot is available (simplified)
    # In production, check against booking schedule
    from datetime import datetime
    try:
        requested_datetime = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
        
        # Check if tutor has existing booking at this time
        conflicting_booking = Booking.query.filter(
            Booking.tutor_id == tutor_id,
            Booking.schedule_date == requested_datetime.date(),
            Booking.schedule_time == time_str,
            Booking.status.in_(['pending', 'confirmed'])
        ).first()
        
        available = conflicting_booking is None
        
        return jsonify({
            'success': True,
            'available': available,
            'tutor_name': tutor.full_name,
            'requested_time': requested_datetime.isoformat(),
            'next_available': get_next_available_slot(tutor_id) if not available else None
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date/time format. Use YYYY-MM-DD and HH:MM'
        }), 400

# Helper functions
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km (Haversine formula)"""
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def check_tutor_availability(tutor_id):
    """Check if tutor is currently available"""
    # Simplified check - in production, check schedule
    import random
    return random.choice([True, False])

def get_subject_expertise(tutor_id):
    """Get tutor's subject expertise breakdown"""
    # Mock data - in production, analyze bookings
    return {
        'Mathematics': 85,
        'Physics': 75,
        'Chemistry': 65,
        'English': 90
    }

def get_next_available_slot(tutor_id):
    """Get next available time slot for tutor"""
    # Mock function - in production, query schedule
    from datetime import datetime, timedelta
    next_slot = datetime.now() + timedelta(hours=2)
    return {
        'date': next_slot.strftime('%Y-%m-%d'),
        'time': next_slot.strftime('%H:%M'),
        'formatted': next_slot.strftime('%A, %B %d at %I:%M %p')
    }