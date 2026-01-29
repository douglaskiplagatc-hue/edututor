from datetime import datetime, timedelta
from app import db
from app.models import Booking, Tutor, User, Payment
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json

class AnalyticsEngine:
    @staticmethod
    def get_tutor_analytics(tutor_id, period='month'):
        """Get detailed analytics for a tutor"""
        tutor = Tutor.query.get(tutor_id)
        
        if period == 'week':
            days = 7
        elif period == 'month':
            days = 30
        else:  # year
            days = 365
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get bookings data
        bookings = Booking.query.filter(
            Booking.tutor_id == tutor_id,
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        ).all()
        
        # Calculate metrics
        total_bookings = len(bookings)
        completed_bookings = len([b for b in bookings if b.status == 'completed'])
        cancelled_bookings = len([b for b in bookings if b.status == 'cancelled'])
        pending_bookings = len([b for b in bookings if b.status == 'pending'])
        
        # Calculate earnings
        earnings = sum([b.total_amount for b in bookings if b.status == 'completed'])
        
        # Get hourly distribution
        hourly_data = {}
        for hour in range(8, 22):  # 8 AM to 10 PM
            hourly_data[f'{hour}:00'] = len([
                b for b in bookings 
                if b.status == 'completed' and 
                int(b.schedule_time.split(':')[0]) == hour
            ])
        
        # Student retention rate
        unique_students = len(set([b.student_id for b in bookings]))
        repeat_students = len([
            student_id for student_id in 
            [b.student_id for b in bookings]
            if [b.student_id for b in bookings].count(student_id) > 1
        ])
        
        retention_rate = (repeat_students / unique_students * 100) if unique_students > 0 else 0
        
        return {
            'summary': {
                'total_bookings': total_bookings,
                'completed_bookings': completed_bookings,
                'cancellation_rate': (cancelled_bookings / total_bookings * 100) if total_bookings > 0 else 0,
                'completion_rate': (completed_bookings / total_bookings * 100) if total_bookings > 0 else 0,
                'total_earnings': earnings,
                'average_session_value': earnings / completed_bookings if completed_bookings > 0 else 0,
                'retention_rate': retention_rate
            },
            'hourly_distribution': hourly_data,
            'subject_popularity': AnalyticsEngine._get_subject_popularity(tutor_id),
            'trend_data': AnalyticsEngine._get_trend_data(tutor_id, days),
            'student_feedback': AnalyticsEngine._get_feedback_analytics(tutor_id)
        }
    
    @staticmethod
    def _get_subject_popularity(tutor_id):
        """Get subject popularity analysis"""
        bookings = Booking.query.filter_by(tutor_id=tutor_id).all()
        
        subject_counts = {}
        for booking in bookings:
            subject = booking.subject
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
        
        return sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    @staticmethod
    def _get_trend_data(tutor_id, days):
        """Get booking trends over time"""
        dates = []
        bookings_count = []
        earnings_data = []
        
        for i in range(days, 0, -1):
            date = datetime.utcnow() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            daily_bookings = Booking.query.filter(
                Booking.tutor_id == tutor_id,
                Booking.created_at >= start_of_day,
                Booking.created_at <= end_of_day
            ).all()
            
            dates.append(date.strftime('%Y-%m-%d'))
            bookings_count.append(len(daily_bookings))
            earnings_data.append(sum([b.total_amount for b in daily_bookings if b.status == 'completed']))
        
        return {
            'dates': dates,
            'bookings': bookings_count,
            'earnings': earnings_data
        }
    
    @staticmethod
    def _get_feedback_analytics(tutor_id):
        """Get feedback and rating analytics"""
        from app.models import Review
        
        reviews = Review.query.filter_by(tutor_id=tutor_id).all()
        
        if not reviews:
            return {}
        
        ratings = [r.rating for r in reviews]
        
        return {
            'average_rating': sum(ratings) / len(ratings),
            'total_reviews': len(reviews),
            'rating_distribution': {
                '5_stars': len([r for r in ratings if r == 5]),
                '4_stars': len([r for r in ratings if r == 4]),
                '3_stars': len([r for r in ratings if r == 3]),
                '2_stars': len([r for r in ratings if r == 2]),
                '1_star': len([r for r in ratings if r == 1])
            },
            'recent_feedback': [
                {
                    'rating': r.rating,
                    'comment': r.comment[:100] + '...' if len(r.comment) > 100 else r.comment,
                    'date': r.created_at.strftime('%Y-%m-%d'),
                    'student': r.author.username
                }
                for r in reviews[:5]
            ]
        }