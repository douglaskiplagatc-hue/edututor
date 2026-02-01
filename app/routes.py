from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    abort,
)
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import url_parse
from app import db
from app.models import User, Tutor, Booking, Review, Message, Payment, Notification
from app.forms import (
    StudentRegistrationForm,
    LoginForm,
    TutorProfileForm,
    BookingForm,
    MessageForm,
    TutorProfileForm,
    ReviewForm,
    TutorRegistrationForm,
    ChangePasswordForm,
    StudentRegistrationForm,
    UserProfileForm,
)

from app.utils import save_picture, hometutor_required, student_required
from datetime import datetime, date
from datetime import datetime, date
from sqlalchemy.orm import joinedload
import os

# Create Blueprintsb
main = Blueprint("main", __name__)
auth = Blueprint("auth", __name__)
hometutor = Blueprint("tutor", __name__)
api = Blueprint("api", __name__)

# ====================
# MAIN ROUTES
# ====================


@main.route("/")
def landing():
    return render_template("landing.html")


@main.route("/home")
@main.route("/home")
def index():
    """Home page"""
    # Get featured tutors (top-rated)
    featured_tutors = (
        Tutor.query.join(User)
        .filter(User.is_verified.is_(True), Tutor.is_available.is_(True))
        .options(joinedload(Tutor.user))
        .all()
    )

    # Statistics (in real app, calculate from database)
    stats = {
        "tutors": Tutor.query.join(User)
        .filter(User.is_verified == True, Tutor.is_available == True)
        .count()
        or 120,
        "subjects": 25,
        "students": User.query.filter_by(user_type="student").count() or 850,
        "locations": 8,
    }

    return render_template(
        "index.html",
        tutors=featured_tutors,
        stats=stats,
        title="Home - Find Quality Tutors in Kenya",
    )


@main.route("/tutors")
def tutors():
    """Browse tutors page"""
    page = request.args.get("page", 1, type=int)
    per_page = 12

    # Get filter parameters
    subject_filter = request.args.get("subject", "")
    location_filter = request.args.get("location", "")
    level_filter = request.args.get("level", "")
    min_rate = request.args.get("min_rate", type=int)
    max_rate = request.args.get("max_rate", type=int)

    # Build query
    subject = "English"
    location = "Mombasa"

    query = Tutor.query.join(User, Tutor.user_id == User.id).filter(
        User.is_verified == True,
        Tutor.is_available == True,
        Tutor.subjects.ilike(f"%{subject}%"),
        User.location == location,
    )
    page = 1
    per_page = 12

    tutors_paginated = query.order_by(Tutor.rating.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    # Apply filters
    if subject_filter:
        query = query.filter(Tutor.subjects.ilike(f"%{subject_filter}%"))
    if location_filter:
        query = query.join(User).filter(User.location == location_filter)
    if level_filter:
        query = query.filter(Tutor.level == level_filter)
    if min_rate:
        query = query.filter(Tutor.hourly_rate >= min_rate)
    if max_rate:
        query = query.filter(Tutor.hourly_rate <= max_rate)

    # Paginate results
    tutors_paginated = query.order_by(Tutor.rating.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get all locations for filter dropdown
    locations = (
        db.session.query(User.location)
        .filter(User.is_verified.is_(True))
        .distinct()
        .all()
    )
    locations = [loc[0] for loc in locations]

    return render_template(
        "tutors.html",
        tutors=tutors_paginated,
        locations=locations,
        filters={
            "subject": subject_filter,
            "location": location_filter,
            "level": level_filter,
            "min_rate": min_rate,
            "max_rate": max_rate,
        },
        title="Find Tutors - EduTutor Kenya",
    )


@main.route("/tutor/<int:tutor_id>")
def tutor_detail(tutor_id):
    """Tutor profile detail page"""
    tutor = Tutor.query.get_or_404(tutor_id)

    # Get reviews for this tutor
    reviews = (
        Review.query.filter_by(tutor_id=tutor_id, is_approved=True)
        .order_by(Review.created_at.desc())
        .all()
    )

    # Check if current user has booked this tutor
    has_booked = False
    if current_user.is_authenticated:
        booking = Booking.query.filter_by(
            student_id=current_user.id, tutor_id=tutor_id, status="completed"
        ).first()
        has_booked = booking is not None

    # Check if user has already reviewed
    has_reviewed = False
    if current_user.is_authenticated:
        review = Review.query.filter_by(
            tutor_id=tutor_id, author_id=current_user.id
        ).first()
        has_reviewed = review is not None

    return render_template(
        "tutor_detail.html",
        tutor=tutor,
        reviews=reviews,
        has_booked=has_booked,
        has_reviewed=has_reviewed,
        title=f"{tutor.full_name} - Tutor Profile",
    )


@main.route("/about")
def about():
    """About us page"""
    return render_template("about.html", title="About Us - EduTutor Kenya")


@main.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact us page"""
    form = ContactForm()
    if form.validate_on_submit():
        # Here you would typically save to database or send email
        flash("Thank you for your message! We will respond within 24 hours.", "success")
        return redirect(url_for("main.contact"))

    return render_template("contact.html", form=form, title="Contact Us")


@main.route("/privacy")
def privacy():
    """Privacy policy page"""
    return render_template("privacy.html", title="Privacy Policy")


@main.route("/terms")
def terms():
    """Terms of service page"""
    return render_template("terms.html", title="Terms of Service")


# ====================
# AUTH ROUTES
# ====================


@auth.route("/login", methods=["GET", "POST"])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            if user.is_active:
                login_user(user, remember=form.remember.data)
                next_page = request.args.get("next")

                # Redirect based on user type
                if user.user_type == "admin" or user.user_type == "super_admin":
                    return redirect(
                        next_page if next_page else url_for("admin.dashboard")
                    )
                elif user.user_type == "tutor":
                    return redirect(
                        next_page if next_page else url_for("tutor.dashboard")
                    )
                else:
                    return redirect(
                        next_page if next_page else url_for("student.dashboard")
                    )
            else:
                flash(
                    "Your account has been deactivated. Please contact support.",
                    "danger",
                )
        else:
            flash("Login unsuccessful. Please check email and password.", "danger")

    return render_template("auth/login.html", form=form)


@auth.route("/register", methods=["GET", "POST"])
def register():
    """User registration with type selection"""
    user_type = request.args.get("user_type", "student")

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if user_type == "student":
        form = StudentRegistrationForm()
        template = "auth/register_student.html"
    elif user_type == "tutor":
        form = TutorRegistrationForm()
        template = "auth/register_tutor.html"
    else:
        # Show selection page
        return render_template("auth/register_choice.html")

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )

        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            password_hash=hashed_password,
            full_name=form.full_name.data,
            user_type=user_type,
            is_active=True,
        )

        db.session.add(user)
        db.session.commit()

        # Create tutor profile if applicable
        if user_type == "tutor":
            from app.models import Tutor

            tutor = Tutor(
                user_id=user.id,
                full_name=form.full_name.data,
                subjects=",".join(form.subjects.data),
                education_levels=",".join(form.education_levels.data),
                hourly_rate=form.hourly_rate.data,
                experience_years=form.experience_years.data,
                location=form.location.data,
                bio=form.bio.data,
                teaching_approach=form.teaching_approach.data,
            )
            db.session.add(tutor)
            db.session.commit()

        flash(
            f"Your {user_type} account has been created! You can now log in.", "success"
        )
        return redirect(url_for("auth.login"))

    return render_template(template, form=form, user_type=user_type)




@auth.route("/logout")
def logout():
    """User logout"""
    logout_user()
    flash("👋 You have been logged out successfully.", "info")
    return redirect(url_for("main.index"))


@auth.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile page"""
    form = ProfileUpdateForm()

    if form.validate_on_submit():
        if form.profile_picture.data:
            picture_file = save_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.location = form.location.data

        db.session.commit()
        flash("✅ Your profile has been updated!", "success")
        return redirect(url_for("auth.profile"))

    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.location.data = current_user.location

    return render_template("profile.html", form=form, title="My Profile")


# ====================
# TUTOR ROUTES
# ====================


@hometutor.route("/dashboard")
@login_required
def dashboard():
    """User dashboard (different for students and tutors)"""
    if current_user.user_type == "tutor":
        # Tutor dashboard
        tutor = Tutor.query.filter_by(user_id=current_user.id).first()

        if not tutor:
            flash("⚠️ Please complete your tutor profile first.", "warning")
            return redirect(url_for("tutor.become_tutor"))

        # Get recent bookings
        bookings = (
            Booking.query.filter_by(tutor_id=tutor.id)
            .order_by(Booking.created_at.desc())
            .limit(10)
            .all()
        )

        # Statistics
        total_bookings = Booking.query.filter_by(tutor_id=tutor.id).count()
        completed_bookings = Booking.query.filter_by(
            tutor_id=tutor.id, status="completed"
        ).count()
        pending_bookings = Booking.query.filter_by(
            tutor_id=tutor.id, status="pending"
        ).count()

        return render_template(
            "tutor_dashboard.html",
            tutor=tutor,
            bookings=bookings,
            stats={
                "total": total_bookings,
                "completed": completed_bookings,
                "pending": pending_bookings,
                "earnings": tutor.hourly_rate * completed_bookings * 2,  # Estimate
            },
            title="Tutor Dashboard",
        )

    else:
        # Student/Parent dashboard
        bookings = (
            Booking.query.filter_by(student_id=current_user.id)
            .order_by(Booking.created_at.desc())
            .all()
        )

        # Get recommended tutors
        recommended_tutors = (
            Tutor.query.filter_by(is_verified=True)
            .order_by(Tutor.rating.desc())
            .limit(3)
            .all()
        )

        return render_template(
            "student_dashboard.html",
            bookings=bookings,
            recommended_tutors=recommended_tutors,
            title="My Dashboard",
        )


@hometutor.route("/become-tutor", methods=["GET", "POST"])
@login_required
def become_tutor():
    """Become a tutor form"""
    # Check if already a tutor
    if current_user.user_type == "tutor":
        tutor = Tutor.query.filter_by(user_id=current_user.id).first()
        if tutor:
            flash("⚠️ You already have a tutor profile!", "info")
            return redirect(url_for("tutor.dashboard"))

    form = TutorProfileForm()

    if form.validate_on_submit():
        # Update user type to tutor
        current_user.user_type = "tutor"

        # Create tutor profile
        tutor = Tutor(
            user_id=current_user.id,
            full_name=form.full_name.data,
            qualifications=form.qualifications.data,
            subjects=form.subjects.data,
            level=form.level.data,
            experience_years=form.experience_years.data,
            hourly_rate=form.hourly_rate.data,
            availability=form.availability.data,
            teaching_mode=form.teaching_mode.data,
            bio=form.bio.data,
        )

        if form.profile_picture.data:
            picture_file = save_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file

        db.session.add(tutor)
        db.session.commit()

        flash(
            "🎉 Tutor profile created successfully! It will be reviewed within 24 hours.",
            "success",
        )
        return redirect(url_for("tutor.dashboard"))

    return render_template("become_tutor.html", form=form, title="Become a Tutor")


@hometutor.route("/book/<int:tutor_id>", methods=["GET", "POST"])
@login_required
def book_tutor(tutor_id):
    """Book a tutor session"""
    tutor = Tutor.query.get_or_404(tutor_id)

    # Check if tutor is available
    if not tutor.is_available:
        flash("⚠️ This tutor is currently not accepting new bookings.", "warning")
        return redirect(url_for("main.tutor_detail", tutor_id=tutor_id))

    form = BookingForm()

    # Set minimum date to tomorrow
    form.schedule_date.render_kw = {
        "min": (date.today() + timedelta(days=1)).isoformat()
    }

    if form.validate_on_submit():
        # Calculate total amount
        total_amount = tutor.hourly_rate * form.hours.data

        # Create booking
        booking = Booking(
            student_id=current_user.id,
            tutor_id=tutor_id,
            subject=form.subject.data,
            hours=form.hours.data,
            total_amount=total_amount,
            location=form.location.data,
            schedule_date=form.schedule_date.data,
            schedule_time=form.schedule_time.data,
            notes=form.notes.data,
            status="pending",
            payment_status="pending",
        )

        db.session.add(booking)
        db.session.commit()

        # Create notification for tutor
        notification = Notification(
            user_id=tutor.user_id,
            title="New Booking Request",
            message=f"{current_user.username} has requested a booking for {form.subject.data}",
            notification_type="booking",
            related_id=booking.id,
        )

        db.session.add(notification)
        db.session.commit()

        flash(
            "✅ Booking request sent successfully! The tutor will respond within 24 hours.",
            "success",
        )
        return redirect(url_for("tutor.dashboard"))

    return render_template(
        "book_tutor.html", tutor=tutor, form=form, title=f"Book {tutor.full_name}"
    )


@hometutor.route("/booking/<int:booking_id>")
@login_required
def booking_detail(booking_id):
    """View booking details"""
    booking = Booking.query.get_or_404(booking_id)

    # Check authorization
    if (
        booking.student_id != current_user.id
        and booking.tutor.user_id != current_user.id
    ):
        abort(403)

    return render_template(
        "booking_detail.html", booking=booking, title=f"Booking #{booking_id}"
    )


@hometutor.route("/booking/<int:booking_id>/confirm")
@login_required
@hometutor_required
def confirm_booking(booking_id):
    """Tutor confirms a booking"""
    booking = Booking.query.get_or_404(booking_id)

    # Check if current user is the tutor
    tutor = Tutor.query.filter_by(user_id=current_user.id).first()
    if booking.tutor_id != tutor.id:
        abort(403)

    booking.status = "confirmed"
    db.session.commit()

    flash("✅ Booking confirmed successfully!", "success")
    return redirect(url_for("tutor.dashboard"))


@hometutor.route("/booking/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    """Cancel a booking"""
    booking = Booking.query.get_or_404(booking_id)

    # Check authorization
    if (
        booking.student_id != current_user.id
        and booking.tutor.user_id != current_user.id
    ):
        abort(403)

    booking.status = "cancelled"
    db.session.commit()

    flash("Booking cancelled successfully.", "info")
    return redirect(url_for("tutor.dashboard"))


@hometutor.route("/tutor/<int:tutor_id>/review", methods=["POST"])
@login_required
def submit_review(tutor_id):
    """Submit a review for a tutor"""
    tutor = Tutor.query.get_or_404(tutor_id)
    form = ReviewForm()

    if form.validate_on_submit():
        # Check if user has completed a booking with this tutor
        completed_booking = Booking.query.filter_by(
            student_id=current_user.id, tutor_id=tutor_id, status="completed"
        ).first()

        if not completed_booking:
            flash(
                "❌ You can only review tutors you have completed sessions with.",
                "danger",
            )
            return redirect(url_for("main.tutor_detail", tutor_id=tutor_id))

        # Check if already reviewed
        existing_review = Review.query.filter_by(
            author_id=current_user.id, tutor_id=tutor_id
        ).first()

        if existing_review:
            flash("⚠️ You have already reviewed this tutor.", "warning")
            return redirect(url_for("main.tutor_detail", tutor_id=tutor_id))

        # Create review
        review = Review(
            tutor_id=tutor_id,
            author_id=current_user.id,
            booking_id=completed_booking.id,
            rating=form.rating.data,
            comment=form.comment.data,
        )

        db.session.add(review)

        # Update tutor rating
        tutor.update_rating(form.rating.data)

        # Mark booking as reviewed
        completed_booking.is_reviewed = True

        db.session.commit()

        flash(
            "✅ Review submitted successfully! Thank you for your feedback.", "success"
        )

    return redirect(url_for("main.tutor_detail", tutor_id=tutor_id))


# ====================
# API ROUTES
# ====================


@api.route("/tutors/search")
def search_tutors():
    """API endpoint for tutor search (AJAX)"""
    query = request.args.get("q", "")
    location = request.args.get("location", "")
    subject = request.args.get("subject", "")
    limit = request.args.get("limit", 10, type=int)

    # Build query
    tutors_query = Tutor.query.filter_by(is_verified=True, is_available=True)

    if query:
        tutors_query = tutors_query.filter(
            Tutor.full_name.ilike(f"%{query}%") | Tutor.subjects.ilike(f"%{query}%")
        )

    if location:
        tutors_query = tutors_query.join(User).filter(User.location == location)

    if subject:
        tutors_query = tutors_query.filter(Tutor.subjects.ilike(f"%{subject}%"))

    tutors = tutors_query.order_by(Tutor.rating.desc()).limit(limit).all()

    # Format response
    result = []
    for tutor in tutors:
        result.append(
            {
                "id": tutor.id,
                "name": tutor.full_name,
                "subjects": tutor.subjects,
                "location": tutor.user.location,
                "rate": tutor.hourly_rate,
                "rating": tutor.rating,
                "experience": tutor.experience_years,
                "image": url_for(
                    "static", filename=f"uploads/{tutor.user.profile_picture}"
                )
                if tutor.user.profile_picture != "default-avatar.png"
                else url_for("static", filename="images/default-avatar.png"),
                "url": url_for("main.tutor_detail", tutor_id=tutor.id),
            }
        )

    return jsonify(result)


@api.route("/booking/<int:booking_id>/status", methods=["PUT"])
@login_required
def update_booking_status(booking_id):
    """API endpoint to update booking status"""
    booking = Booking.query.get_or_404(booking_id)

    # Check authorization
    if (
        booking.student_id != current_user.id
        and booking.tutor.user_id != current_user.id
    ):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    new_status = data.get("status")

    if new_status in ["confirmed", "cancelled", "completed"]:
        booking.status = new_status
        booking.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "status": new_status,
                "status_display": booking.get_status_display(),
            }
        )

    return jsonify({"error": "Invalid status"}), 400


@api.route("/notifications")
@login_required
def get_notifications():
    """Get user notifications"""
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )

    result = []
    for notification in notifications:
        result.append(
            {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "type": notification.notification_type,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
                "time_ago": get_time_ago(notification.created_at),
            }
        )

    return jsonify(result)


@api.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    notification.is_read = True
    db.session.commit()

    return jsonify({"success": True})


@api.route("/stats")
@login_required
def get_stats():
    """Get dashboard statistics"""
    if current_user.user_type == "tutor":
        tutor = Tutor.query.filter_by(user_id=current_user.id).first()
        if not tutor:
            return jsonify({"error": "Tutor profile not found"}), 404

        total_bookings = Booking.query.filter_by(tutor_id=tutor.id).count()
        completed_bookings = Booking.query.filter_by(
            tutor_id=tutor.id, status="completed"
        ).count()
        pending_bookings = Booking.query.filter_by(
            tutor_id=tutor.id, status="pending"
        ).count()
        monthly_earnings = (
            tutor.hourly_rate * completed_bookings * 2
        )  # Simplified calculation

        return jsonify(
            {
                "total_bookings": total_bookings,
                "completed_bookings": completed_bookings,
                "pending_bookings": pending_bookings,
                "monthly_earnings": monthly_earnings,
                "rating": tutor.rating,
                "review_count": tutor.review_count,
            }
        )
    else:
        total_bookings = Booking.query.filter_by(student_id=current_user.id).count()
        completed_bookings = Booking.query.filter_by(
            student_id=current_user.id, status="completed"
        ).count()

        upcoming_bookings = Booking.query.filter(
            Booking.student_id == current_user.id,
            Booking.status == "confirmed",
            Booking.schedule_date >= date.today(),
        ).count()
        return jsonify(
            {
                "total_bookings": total_bookings,
                "completed_bookings": completed_bookings,
                "upcoming_bookings": upcoming_bookings,
            }
        )


# Helper function
def get_time_ago(dt):
    """Calculate time ago string"""
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


# Error handlers
@main.app_errorhandler(404)
def not_found_error(error):
    return render_template("templates/errors/404.html"), 404


@main.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("templates/errors/500.html"), 500


@main.app_errorhandler(403)
def forbidden_error(error):
    return render_template("templates/errors/403.html"), 403


@main.route("/test")
def test():
    """Simple test route to check template loading"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body style="background: #f0f0f0; padding: 20px;">
        <h1 style="color: green;">✅ Flask is Working!</h1>
        <p>If you can see this, Flask is running correctly.</p>
        <p>Now test templates:</p>
        <ul>
            <li><a href="/simple">Simple Template Test</a></li>
            <li><a href="/">Home Page</a></li>
        </ul>
    </body>
    </html>
    """


from datetime import datetime
import os


@main.route("/simple")
def simple_template():
    """Test template loading with minimal template"""
    template_path = os.path.join(
        os.path.dirname(__file__), "templates", "simple_test.html"
    )
    return render_template(
        "simple_test.html",
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        template_path=template_path,
        error=None,
    )


# ====================
# MOBILE API ENDPOINTS
# ====================


@api.route("/mobile/login", methods=["POST"])
def mobile_login():
    """Mobile login with JWT tokens"""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    device_token = data.get("device_token")  # For push notifications

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        # Generate JWT token
        import jwt
        import datetime

        token = jwt.encode(
            {
                "user_id": user.id,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
            },
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        # Update device token for push notifications
        if device_token:
            user.device_token = device_token
            db.session.commit()

        return jsonify(
            {
                "success": True,
                "token": token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "user_type": user.user_type,
                    "profile_picture": user.profile_picture,
                },
            }
        )

    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@api.route("/mobile/tutors/nearby", methods=["GET"])
def nearby_tutors():
    """Get tutors near user's location"""
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    radius = request.args.get("radius", 10, type=float)  # km

    # For now, return all tutors (implement geolocation later)
    tutors = Tutor.query.filter_by(is_verified=True, is_available=True).all()

    result = []
    for tutor in tutors:
        result.append(
            {
                "id": tutor.id,
                "name": tutor.full_name,
                "subjects": tutor.subjects,
                "rate": tutor.hourly_rate,
                "rating": tutor.rating,
                "distance": 5.2,  # Mock distance
                "available_now": True,
            }
        )

    return jsonify({"tutors": result})


@api.route("/mobile/booking/quick", methods=["POST"])
@login_required
def quick_booking():
    """Quick booking for mobile"""
    data = request.get_json()

    # Create instant booking
    booking = Booking(
        student_id=current_user.id,
        tutor_id=data["tutor_id"],
        subject=data["subject"],
        hours=1,
        total_amount=data.get("amount", 500),
        schedule_date=datetime.utcnow().date(),
        schedule_time="ASAP",
        status="pending",
        is_quick_booking=True,
    )

    db.session.add(booking)
    db.session.commit()

    # Send push notification to tutor
    send_push_notification(
        booking.tutor.user.device_token,
        "New Quick Booking Request",
        f"{current_user.username} wants a session now!",
    )

    return jsonify(
        {"success": True, "booking_id": booking.id, "message": "Booking request sent"}
    )


@api.route("/mobile/notifications", methods=["GET"])
@login_required
def mobile_notifications():
    """Get notifications for mobile"""
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )

    result = []
    for notif in notifications:
        result.append(
            {
                "id": notif.id,
                "title": notif.title,
                "body": notif.message,
                "type": notif.notification_type,
                "timestamp": notif.created_at.isoformat(),
                "read": notif.is_read,
                "data": {"booking_id": notif.related_id},
            }
        )

    return jsonify({"notifications": result})
