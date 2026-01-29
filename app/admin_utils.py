from functools import wraps
from flask import abort, jsonify, request, current_app
from flask_login import current_user
import json

def admin_required(f):
    """Decorator to restrict access to admins only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.user_type != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator for super admin only (can manage other admins)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.user_type != 'admin' or not current_user.is_super_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def log_admin_action(action, resource_type=None, resource_id=None, details=None):
    """Log admin actions for audit trail"""
    from app.models import AdminAuditLog, db
    
    log = AdminAuditLog(
        admin_id=current_user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    db.session.add(log)
    db.session.commit()

def get_admin_stats():
    """Get dashboard statistics for admin"""
    from app.models import User, Tutor, Booking, Payment, SupportTicket, db
    from datetime import datetime, timedelta
    
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User statistics
    total_users = User.query.count()
    new_users_today = User.query.filter(
        db.func.date(User.created_at) == today
    ).count()
    new_users_week = User.query.filter(
        User.created_at >= week_ago
    ).count()
    
    # Tutor statistics
    total_tutors = Tutor.query.count()
    pending_tutors = Tutor.query.filter_by(is_verified=False).count()
    new_tutors_week = Tutor.query.filter(
        Tutor.created_at >= week_ago
    ).count()
    
    # Booking statistics
    total_bookings = Booking.query.count()
    today_bookings = Booking.query.filter(
        db.func.date(Booking.created_at) == today
    ).count()
    week_bookings = Booking.query.filter(
        Booking.created_at >= week_ago
    ).count()
    
    # Financial statistics
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed'
    ).scalar() or 0
    
    today_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        db.func.date(Payment.created_at) == today
    ).scalar() or 0
    
    week_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.created_at >= week_ago
    ).scalar() or 0
    
    # Support statistics
    open_tickets = SupportTicket.query.filter_by(status='open').count()
    urgent_tickets = SupportTicket.query.filter_by(priority='urgent', status='open').count()
    
    # Platform metrics
    completion_rate = 0
    if total_bookings > 0:
        completed_bookings = Booking.query.filter_by(status='completed').count()
        completion_rate = (completed_bookings / total_bookings) * 100
    
    average_rating = db.session.query(db.func.avg(Tutor.rating)).scalar() or 0
    
    return {
        'users': {
            'total': total_users,
            'today': new_users_today,
            'week': new_users_week,
            'students': User.query.filter_by(user_type='student').count(),
            'tutors': total_tutors,
            'parents': User.query.filter_by(user_type='parent').count(),
            'admins': User.query.filter_by(user_type='admin').count()
        },
        'tutors': {
            'total': total_tutors,
            'pending_verification': pending_tutors,
            'new_week': new_tutors_week,
            'verified': Tutor.query.filter_by(is_verified=True).count(),
            'featured': Tutor.query.filter_by(is_featured=True).count(),
            'online': Tutor.query.filter_by(is_available=True).count()
        },
        'bookings': {
            'total': total_bookings,
            'today': today_bookings,
            'week': week_bookings,
            'pending': Booking.query.filter_by(status='pending').count(),
            'confirmed': Booking.query.filter_by(status='confirmed').count(),
            'completed': Booking.query.filter_by(status='completed').count(),
            'cancelled': Booking.query.filter_by(status='cancelled').count()
        },
        'financial': {
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
            'week_revenue': week_revenue,
            'platform_fee': total_revenue * 0.15,  # 15% platform fee
            'tutor_payouts': total_revenue * 0.85,
            'pending_payouts': db.session.query(db.func.sum(Payment.amount)).filter(
                Payment.status == 'pending'
            ).scalar() or 0
        },
        'support': {
            'open_tickets': open_tickets,
            'urgent_tickets': urgent_tickets,
            'total_tickets': SupportTicket.query.count(),
            'resolved_today': SupportTicket.query.filter(
                SupportTicket.status == 'resolved',
                db.func.date(SupportTicket.resolved_at) == today
            ).count()
        },
        'platform_metrics': {
            'completion_rate': round(completion_rate, 1),
            'average_rating': round(average_rating, 1),
            'response_time': '2.5 hours',  # Mock data
            'satisfaction_score': 4.5,  # Mock data
            'active_users': User.query.filter(
                User.last_login >= month_ago
            ).count()
        }
    }

def get_chart_data(period='week'):
    """Get chart data for admin dashboard"""
    from app.models import Booking, Payment, User, db
    from datetime import datetime, timedelta
    
    if period == 'week':
        days = 7
    elif period == 'month':
        days = 30
    else:  # year
        days = 365
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    dates = []
    bookings_data = []
    revenue_data = []
    users_data = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        dates.append(date_str)
        
        # Get bookings for this day
        bookings_count = Booking.query.filter(
            db.func.date(Booking.created_at) == date.date()
        ).count()
        bookings_data.append(bookings_count)
        
        # Get revenue for this day
        revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            db.func.date(Payment.created_at) == date.date()
        ).scalar() or 0
        revenue_data.append(float(revenue))
        
        # Get new users for this day
        new_users = User.query.filter(
            db.func.date(User.created_at) == date.date()
        ).count()
        users_data.append(new_users)
    
    return {
        'dates': dates,
        'bookings': bookings_data,
        'revenue': revenue_data,
        'users': users_data,
        'period': period
    }

def export_data(resource_type, format='csv', filters=None):
    """Export data in various formats"""
    import csv
    import json
    from io import StringIO
    from app.models import User, Tutor, Booking, Payment
    
    if resource_type == 'users':
        query = User.query
        if filters:
            if filters.get('user_type'):
                query = query.filter_by(user_type=filters['user_type'])
            if filters.get('is_active') is not None:
                query = query.filter_by(is_active=filters['is_active'])
        data = query.all()
        
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Username', 'Email', 'Phone', 'User Type', 'Location', 'Created At'])
            for user in data:
                writer.writerow([
                    user.id, user.username, user.email, user.phone,
                    user.user_type, user.location, user.created_at
                ])
            return output.getvalue()
        
        elif format == 'json':
            return json.dumps([{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'phone': u.phone,
                'user_type': u.user_type,
                'location': u.location,
                'created_at': u.created_at.isoformat()
            } for u in data], indent=2)
    
    elif resource_type == 'tutors':
        query = Tutor.query.join(User)
        if filters:
            if filters.get('is_verified') is not None:
                query = query.filter_by(is_verified=filters['is_verified'])
            if filters.get('is_available') is not None:
                query = query.filter_by(is_available=filters['is_available'])
        data = query.all()
        
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Full Name', 'Email', 'Phone', 'Subjects', 'Rate', 'Rating', 'Verified', 'Created At'])
            for tutor in data:
                writer.writerow([
                    tutor.id, tutor.full_name, tutor.user.email, tutor.user.phone,
                    tutor.subjects, tutor.hourly_rate, tutor.rating,
                    tutor.is_verified, tutor.created_at
                ])
            return output.getvalue()
    
    elif resource_type == 'bookings':
        query = Booking.query
        if filters:
            if filters.get('status'):
                query = query.filter_by(status=filters['status'])
            if filters.get('date_from'):
                query = query.filter(Booking.created_at >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(Booking.created_at <= filters['date_to'])
        data = query.all()
        
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Student', 'Tutor', 'Subject', 'Hours', 'Amount', 'Status', 'Created At'])
            for booking in data:
                writer.writerow([
                    booking.id, booking.student.username, booking.tutor.full_name,
                    booking.subject, booking.hours, booking.total_amount,
                    booking.status, booking.created_at
                ])
            return output.getvalue()
    
    elif resource_type == 'payments':
        query = Payment.query
        if filters:
            if filters.get('status'):
                query = query.filter_by(status=filters['status'])
        data = query.all()
        
        if format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['ID', 'Booking ID', 'Amount', 'Status', 'M-Pesa Receipt', 'Phone', 'Created At'])
            for payment in data:
                writer.writerow([
                    payment.id, payment.booking_id, payment.amount,
                    payment.status, payment.mpesa_receipt or '',
                    payment.phone_number or '', payment.created_at
                ])
            return output.getvalue()
    
    return None
# admin_utils.py (additional functions)

import csv
import json
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_, or_
from app.models import (
    User, Tutor, Booking, Payment, Review, SupportTicket,
    AdminAuditLog, PlatformSetting
)

def get_admin_stats():
    """Get admin dashboard statistics"""
    now = datetime.utcnow()
    last_week = now - timedelta(days=7)
    last_month = now - timedelta(days=30)
    
    stats = {
        # User statistics
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_tutors': Tutor.query.filter_by(is_verified=True).count(),
        'total_students': User.query.filter_by(user_type='student', is_active=True).count(),
        'new_users_week': User.query.filter(
            User.created_at >= last_week,
            User.is_active == True
        ).count(),
        'new_users_month': User.query.filter(
            User.created_at >= last_month,
            User.is_active == True
        ).count(),
        
        # Booking statistics
        'total_bookings': Booking.query.count(),
        'pending_bookings': Booking.query.filter_by(status='pending').count(),
        'completed_bookings': Booking.query.filter_by(status='completed').count(),
        'cancelled_bookings': Booking.query.filter_by(status='cancelled').count(),
        'weekly_bookings': Booking.query.filter(Booking.created_at >= last_week).count(),
        'monthly_bookings': Booking.query.filter(Booking.created_at >= last_month).count(),
        
        # Payment statistics
        'total_revenue': db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed'
        ).scalar() or 0,
        'pending_payments': Payment.query.filter_by(status='pending').count(),
        'weekly_revenue': db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.created_at >= last_week
        ).scalar() or 0,
        'monthly_revenue': db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.created_at >= last_month
        ).scalar() or 0,
        
        # Support statistics
        'open_tickets': SupportTicket.query.filter_by(status='open').count(),
        'high_priority_tickets': SupportTicket.query.filter_by(
            status='open', priority='high'
        ).count(),
        
        # Platform statistics
        'average_tutor_rating': db.session.query(func.avg(Tutor.rating)).filter(
            Tutor.rating > 0
        ).scalar() or 0,
        'featured_tutors': Tutor.query.filter_by(is_featured=True).count(),
        'available_tutors': Tutor.query.filter_by(is_available=True).count(),
    }
    
    # Format numbers
    if stats['average_tutor_rating']:
        stats['average_tutor_rating'] = round(stats['average_tutor_rating'], 1)
    
    return stats

def get_chart_data(period='week'):
    """Get chart data for dashboard"""
    now = datetime.utcnow()
    
    if period == 'week':
        days = 7
        date_format = '%a'  # Mon, Tue, etc.
    elif period == 'month':
        days = 30
        date_format = '%d %b'  # 01 Jan, 02 Jan, etc.
    else:
        days = 7
        date_format = '%a'
    
    # Generate dates
    dates = []
    for i in range(days - 1, -1, -1):
        date = now - timedelta(days=i)
        dates.append(date.strftime(date_format))
    
    # Get bookings data
    bookings_data = []
    for i in range(days - 1, -1, -1):
        start_date = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        count = Booking.query.filter(
            Booking.created_at >= start_date,
            Booking.created_at < end_date
        ).count()
        
        bookings_data.append(count)
    
    # Get revenue data
    revenue_data = []
    for i in range(days - 1, -1, -1):
        start_date = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.created_at >= start_date,
            Payment.created_at < end_date
        ).scalar() or 0
        
        revenue_data.append(float(revenue))
    
    # Get user registrations
    users_data = []
    for i in range(days - 1, -1, -1):
        start_date = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        count = User.query.filter(
            User.created_at >= start_date,
            User.created_at < end_date
        ).count()
        
        users_data.append(count)
    
    return {
        'labels': dates,
        'bookings': bookings_data,
        'revenue': revenue_data,
        'users': users_data,
        'period': period
    }

def export_data(data_type, format='csv', filters=None):
    """Export data to CSV or JSON"""
    filters = filters or {}
    
    if data_type == 'users':
        query = User.query
        
        if 'user_type' in filters:
            query = query.filter_by(user_type=filters['user_type'])
        if 'is_active' in filters:
            query = query.filter_by(is_active=filters['is_active'])
        
        data = query.all()
        fields = ['id', 'username', 'email', 'phone', 'user_type', 'is_active', 
                 'is_verified', 'created_at']
        
    elif data_type == 'tutors':
        query = Tutor.query.join(User)
        
        if 'is_verified' in filters:
            query = query.filter_by(is_verified=filters['is_verified'])
        
        data = query.all()
        fields = ['id', 'full_name', 'user.email', 'subjects', 'education_level',
                 'rating', 'hourly_rate', 'is_verified', 'is_featured', 
                 'is_available', 'created_at']
        
    elif data_type == 'bookings':
        query = Booking.query
        
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        
        data = query.all()
        fields = ['id', 'student.username', 'tutor.full_name', 'subject',
                 'duration_hours', 'total_amount', 'status', 'booking_date',
                 'created_at']
        
    elif data_type == 'payments':
        query = Payment.query
        
        if 'status' in filters:
            query = query.filter_by(status=filters['status'])
        
        data = query.all()
        fields = ['id', 'transaction_id', 'user.username', 'amount', 'currency',
                 'payment_method', 'status', 'created_at']
        
    elif data_type == 'reviews':
        query = Review.query
        data = query.all()
        fields = ['id', 'student.username', 'tutor.full_name', 'rating',
                 'comment', 'created_at']
    
    else:
        raise ValueError(f"Unsupported data type: {data_type}")
    
    # Convert to requested format
    if format == 'csv':
        return convert_to_csv(data, fields)
    elif format == 'json':
        return convert_to_json(data, fields)
    else:
        raise ValueError(f"Unsupported format: {format}")

def convert_to_csv(data, fields):
    """Convert data to CSV format"""
    output = BytesIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(fields)
    
    # Write data
    for item in data:
        row = []
        for field in fields:
            if '.' in field:
                # Handle nested fields (e.g., 'user.email')
                parts = field.split('.')
                value = item
                for part in parts:
                    value = getattr(value, part, '')
                row.append(str(value) if value is not None else '')
            else:
                value = getattr(item, field, '')
                if isinstance(value, datetime):
                    row.append(value.isoformat())
                else:
                    row.append(str(value) if value is not None else '')
        
        writer.writerow(row)
    
    return output.getvalue().decode('utf-8')

def convert_to_json(data, fields):
    """Convert data to JSON format"""
    result = []
    
    for item in data:
        obj = {}
        for field in fields:
            if '.' in field:
                parts = field.split('.')
                value = item
                for part in parts:
                    value = getattr(value, part, None)
            else:
                value = getattr(item, field, None)
            
            # Convert datetime to ISO format
            if isinstance(value, datetime):
                value = value.isoformat()
            
            obj[field] = value
        
        result.append(obj)
    
    return json.dumps(result, indent=2)

def log_admin_action(action, resource_type, resource_id, details=None):
    """Log admin action to audit log"""
    audit_log = AdminAuditLog(
        admin_id=current_user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    db.session.add(audit_log)
    db.session.commit()