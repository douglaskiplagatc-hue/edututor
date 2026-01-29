import os
import secrets
from PIL import Image
from flask import current_app, url_for
from functools import wraps
from flask_login import current_user


def save_picture(form_picture):
    """Save uploaded profile picture"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, "static/uploads", picture_fn)

    # Resize image
    output_size = (300, 300)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


def send_reset_email(user):
    """Send password reset email (placeholder)"""
    # In production, integrate with email service like SendGrid
    pass


def send_booking_confirmation(booking):
    """Send booking confirmation email"""
    pass


def send_tutor_notification(tutor, student):
    """Notify tutor of new booking"""
    pass


def calculate_tutor_rating(tutor_id):
    """Recalculate tutor's average rating"""
    from app.models import Review

    reviews = Review.query.filter_by(tutor_id=tutor_id).all()
    if reviews:
        total_rating = sum([review.rating for review in reviews])
        average = total_rating / len(reviews)
        return round(average, 1)
    return 0.0


def format_currency(amount):
    """Format amount as Kenyan Shillings"""
    return f"KSH {amount:,.0f}"


def hometutor_required(f):
    """Decorator to restrict access to tutors only"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != "tutor":
            from flask import flash, redirect, url_for

            flash("This page is only accessible to tutors.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function


def student_required(f):
    """Decorator to restrict access to students only"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_type != "student":
            from flask import flash, redirect, url_for

            flash("This page is only accessible to students.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function
