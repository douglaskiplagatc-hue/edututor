from flask import (
    Blueprint,
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    flash,
    send_file,
)
from flask_login import login_required, current_user
from app import db
from app.models import (
    User,
    Tutor,
    Booking,
    Payment,
    Review,
    SupportTicket,
    AdminAuditLog,
    PlatformSetting,
    Announcement,
    Message,
)
from app.admin_utils import (
    admin_required,
    super_admin_required,
    log_admin_action,
    get_admin_stats,
    get_chart_data,
    export_data,
)
from app.forms import (
    UserProfileForm,
    TutorProfileForm,
    AnnouncementForm,
    PlatformSettingForm,
)
from app.notifications import PushNotificationService
from datetime import datetime, timedelta
from urllib.parse import urlparse  # Python's built-in (works great!)

# OR if you need werkzeug's specific features:
from werkzeug.urls import url_parse  # Note: 'urls' not 'utils'

import json
from io import BytesIO
import csv

admin = Blueprint("admin", __name__, url_prefix="/admin")

# ====================
# ADMIN DASHBOARD
# ====================


@admin.route("/")
@admin.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    stats = get_admin_stats()
    chart_data = get_chart_data("week")

    # Recent activities
    recent_activities = (
        AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(10).all()
    )

    # Recent bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()

    # Recent support tickets
    recent_tickets = (
        SupportTicket.query.filter_by(status="open")
        .order_by(SupportTicket.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        chart_data=chart_data,
        recent_activities=recent_activities,
        recent_bookings=recent_bookings,
        recent_tickets=recent_tickets,
    )


@admin.route("/dashboard/stats")
@login_required
@admin_required
def dashboard_stats():
    """Get dashboard statistics (AJAX)"""
    period = request.args.get("period", "week")
    stats = get_admin_stats()
    chart_data = get_chart_data(period)

    return jsonify({"success": True, "stats": stats, "chart_data": chart_data})


# ====================
# USER MANAGEMENT
# ====================


@admin.route("/users")
@login_required
@admin_required
def users():
    """User management page"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filters
    user_type = request.args.get("type")
    search = request.args.get("search")
    is_active = request.args.get("is_active")

    query = User.query

    if user_type:
        query = query.filter_by(user_type=user_type)

    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
            | (User.phone.ilike(f"%{search}%"))
        )

    if is_active is not None:
        query = query.filter_by(is_active=(is_active.lower() == "true"))

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user_types = db.session.query(User.user_type).distinct().all()
    user_types = [ut[0] for ut in user_types]

    return render_template(
        "admin/users.html", users=users, user_types=user_types, filters=request.args
    )


@admin.route("/users/<int:user_id>")
@login_required
@admin_required
def user_detail(user_id):
    """Get user details"""
    user = User.query.get_or_404(user_id)

    # Get user's bookings
    bookings = (
        Booking.query.filter_by(student_id=user_id)
        .order_by(Booking.created_at.desc())
        .limit(10)
        .all()
    )

    # Get tutor profile if applicable
    tutor = None
    if user.user_type == "tutor":
        tutor = Tutor.query.filter_by(user_id=user_id).first()

    # Get payments
    payments = (
        Payment.query.join(Booking)
        .filter(Booking.student_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "admin/user_detail.html",
        user=user,
        tutor=tutor,
        bookings=bookings,
        payments=payments,
    )


@admin.route("/users/<int:user_id>/update", methods=["POST"])
@login_required
@admin_required
def update_user(user_id):
    """Update user information"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    # Update fields
    if "is_active" in data:
        user.is_active = data["is_active"]
        log_admin_action(
            "update_user_active", "user", user_id, {"is_active": data["is_active"]}
        )

    if "is_verified" in data:
        user.is_verified = data["is_verified"]
        log_admin_action(
            "update_user_verified",
            "user",
            user_id,
            {"is_verified": data["is_verified"]},
        )

    if "user_type" in data and current_user.is_super_admin:
        old_type = user.user_type
        user.user_type = data["user_type"]
        log_admin_action(
            "change_user_type",
            "user",
            user_id,
            {"old_type": old_type, "new_type": data["user_type"]},
        )

    db.session.commit()

    # Send notification to user
    if "is_active" in data and not data["is_active"]:
        PushNotificationService.send_email_notification(
            user.email,
            "Account Status Update",
            "account_deactivated",
            {"username": user.username},
        )

    return jsonify({"success": True, "message": "User updated successfully"})


@admin.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@super_admin_required
def delete_user(user_id):
    """Delete user (super admin only)"""
    if user_id == current_user.id:
        return jsonify(
            {"success": False, "error": "Cannot delete your own account"}
        ), 400

    user = User.query.get_or_404(user_id)

    # Log action before deletion
    log_admin_action(
        "delete_user", "user", user_id, {"username": user.username, "email": user.email}
    )

    # Soft delete (deactivate) instead of hard delete
    user.is_active = False
    user.deleted_at = datetime.utcnow()
    user.deleted_by = current_user.id

    db.session.commit()

    return jsonify({"success": True, "message": "User deactivated successfully"})


@admin.route("/users/export")
@login_required
@admin_required
def export_users():
    """Export users data"""
    filters = {}

    if request.args.get("user_type"):
        filters["user_type"] = request.args.get("user_type")
    if request.args.get("is_active"):
        filters["is_active"] = request.args.get("is_active") == "true"

    format = request.args.get("format", "csv")
    data = export_data("users", format, filters)

    if format == "csv":
        return send_file(
            BytesIO(data.encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
    else:
        return jsonify(json.loads(data))


# ====================
# TUTOR MANAGEMENT
# ====================


@admin.route("/tutors")
@login_required
@admin_required
def tutors():
    """Tutor management page"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filters
    status = request.args.get("status")  # pending, verified, rejected
    search = request.args.get("search")
    min_rating = request.args.get("min_rating", type=float)

    query = Tutor.query.join(User)

    if status == "pending":
        query = query.filter_by(User.is_verified == False)
    elif status == "verified":
        query = query.filter(User.is_verified == True)
    elif status == "rejected":
        query = query.filter(
            User.is_verified == False, User.rejection_reason.isnot(None)
        )
    if search:
        query = query.filter(
            (Tutor.full_name.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
            | (Tutor.subjects.ilike(f"%{search}%"))
        )

    if min_rating:
        query = query.filter(Tutor.rating >= min_rating)

    tutors = query.order_by(Tutor.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template("admin/tutors.html", tutors=tutors, filters=request.args)


@admin.route("/tutors/<int:tutor_id>")
@login_required
@admin_required
def tutor_detail(tutor_id):
    """Get tutor details"""
    tutor = Tutor.query.get_or_404(tutor_id)

    # Get tutor's bookings
    bookings = (
        Booking.query.filter_by(tutor_id=tutor_id)
        .order_by(Booking.created_at.desc())
        .limit(10)
        .all()
    )

    # Get reviews
    reviews = (
        Review.query.filter_by(tutor_id=tutor_id)
        .order_by(Review.created_at.desc())
        .all()
    )

    # Get earnings
    earnings = (
        db.session.query(
            db.func.sum(Booking.total_amount).label("total_earnings"),
            db.func.sum(Booking.tutor_payout).label("tutor_payout"),
            db.func.count(Booking.id).label("total_sessions"),
        )
        .filter(Booking.tutor_id == tutor_id, Booking.status == "completed")
        .first()
    )

    return render_template(
        "admin/tutor_detail.html",
        tutor=tutor,
        bookings=bookings,
        reviews=reviews,
        earnings=earnings,
    )


@admin.route("/tutors/<int:tutor_id>/verify", methods=["POST"])
@login_required
@admin_required
def verify_tutor(tutor_id):
    """Verify/reject tutor"""
    tutor = Tutor.query.get_or_404(tutor_id)
    data = request.get_json()

    action = data.get("action")  # approve, reject
    notes = data.get("notes", "")

    if action == "approve":
        tutor.is_verified = True
        tutor.verified_at = datetime.utcnow()
        tutor.verified_by = current_user.id
        tutor.rejection_reason = None

        log_admin_action("approve_tutor", "tutor", tutor_id, {"notes": notes})

        # Send approval notification
        PushNotificationService.send_email_notification(
            tutor.user.email,
            "Tutor Application Approved! 🎉",
            "tutor_approved",
            {
                "tutor_name": tutor.full_name,
                "approval_date": tutor.verified_at.strftime("%B %d, %Y"),
            },
        )

        PushNotificationService.send_fcm_notification(
            tutor.user.device_token,
            "Application Approved! ✅",
            "Your tutor application has been approved. You can now accept bookings!",
            {"type": "tutor_approved", "tutor_id": tutor.id},
        )

        message = "Tutor approved successfully"

    elif action == "reject":
        tutor.is_verified = False
        tutor.rejection_reason = notes
        tutor.rejected_at = datetime.utcnow()
        tutor.rejected_by = current_user.id

        log_admin_action("reject_tutor", "tutor", tutor_id, {"notes": notes})

        # Send rejection notification
        PushNotificationService.send_email_notification(
            tutor.user.email,
            "Tutor Application Update",
            "tutor_rejected",
            {
                "tutor_name": tutor.full_name,
                "rejection_reason": notes,
                "contact_email": "support@edututor.co.ke",
            },
        )

        message = "Tutor application rejected"

    else:
        return jsonify({"success": False, "error": "Invalid action"}), 400

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": message,
            "tutor": {
                "id": tutor.id,
                "is_verified": tutor.is_verified,
                "verified_at": tutor.verified_at.isoformat()
                if tutor.verified_at
                else None,
                "rejection_reason": tutor.rejection_reason,
            },
        }
    )


@admin.route("/tutors/<int:tutor_id>/feature", methods=["POST"])
@login_required
@admin_required
def feature_tutor(tutor_id):
    """Feature/unfeature a tutor"""
    tutor = Tutor.query.get_or_404(tutor_id)
    data = request.get_json()

    featured = data.get("featured", False)
    tutor.is_featured = featured

    log_admin_action("update_tutor_featured", "tutor", tutor_id, {"featured": featured})

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Tutor {'featured' if featured else 'unfeatured'} successfully",
        }
    )


@admin.route("/tutors/<int:tutor_id>/availability", methods=["POST"])
@login_required
@admin_required
def update_tutor_availability(tutor_id):
    """Update tutor availability"""
    tutor = Tutor.query.get_or_404(tutor_id)
    data = request.get_json()

    available = data.get("available", True)
    tutor.is_available = available

    log_admin_action(
        "update_tutor_availability", "tutor", tutor_id, {"available": available}
    )

    db.session.commit()

    # Notify tutor
    if not available:
        PushNotificationService.send_fcm_notification(
            tutor.user.device_token,
            "Account Status Update",
            "Your tutor profile has been set to unavailable by admin",
            {"type": "availability_updated"},
        )

    return jsonify({"success": True, "message": f"Tutor availability updated"})


# ====================
# BOOKING MANAGEMENT
# ====================


@admin.route("/bookings")
@login_required
@admin_required
def bookings():
    """Booking management page"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filters
    status = request.args.get("status")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    search = request.args.get("search")

    query = Booking.query

    if status:
        query = query.filter_by(status=status)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Booking.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Booking.created_at <= date_to_obj)
        except ValueError:
            pass

    if search:
        query = (
            query.join(User, Booking.student_id == User.id)
            .join(Tutor, Booking.tutor_id == Tutor.id)
            .filter(
                (User.username.ilike(f"%{search}%"))
                | (Tutor.full_name.ilike(f"%{search}%"))
                | (Booking.subject.ilike(f"%{search}%"))
            )
        )

    bookings = query.order_by(Booking.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    statuses = ["pending", "confirmed", "completed", "cancelled"]

    return render_template(
        "admin/bookings.html",
        bookings=bookings,
        statuses=statuses,
        filters=request.args,
    )


@admin.route("/bookings/<int:booking_id>")
@login_required
@admin_required
def booking_detail(booking_id):
    """Get booking details"""
    booking = Booking.query.get_or_404(booking_id)

    # Get payment info
    payment = Payment.query.filter_by(booking_id=booking_id).first()

    # Get messages
    messages = (
        Message.query.filter_by(booking_id=booking_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return render_template(
        "admin/booking_detail.html", booking=booking, payment=payment, messages=messages
    )


@admin.route("/bookings/<int:booking_id>/update-status", methods=["POST"])
@login_required
@admin_required
def update_booking_status(booking_id):
    """Update booking status"""
    booking = Booking.query.get_or_404(booking_id)
    data = request.get_json()

    new_status = data.get("status")
    notes = data.get("notes", "")

    if new_status not in ["pending", "confirmed", "completed", "cancelled"]:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    old_status = booking.status
    booking.status = new_status

    if new_status == "cancelled":
        booking.cancelled_at = datetime.utcnow()
        booking.cancelled_by = "admin"
        booking.cancellation_reason = notes

    log_admin_action(
        "update_booking_status",
        "booking",
        booking_id,
        {"old_status": old_status, "new_status": new_status, "notes": notes},
    )

    db.session.commit()

    # Notify student and tutor
    PushNotificationService.send_fcm_notification(
        booking.student.device_token,
        "Booking Status Updated",
        f"Your booking status has been changed to {new_status} by admin",
        {
            "type": "booking_status_updated",
            "booking_id": booking.id,
            "status": new_status,
        },
    )

    PushNotificationService.send_fcm_notification(
        booking.tutor.user.device_token,
        "Booking Status Updated",
        f"Booking #{booking.id} status changed to {new_status} by admin",
        {
            "type": "booking_status_updated",
            "booking_id": booking.id,
            "status": new_status,
        },
    )

    return jsonify(
        {
            "success": True,
            "message": "Booking status updated",
            "booking": {
                "id": booking.id,
                "status": booking.status,
                "updated_at": booking.updated_at.isoformat()
                if booking.updated_at
                else None,
            },
        }
    )


# ====================
# PAYMENT MANAGEMENT
# ====================

# ====================
# PAYMENT MANAGEMENT (CONTINUED)
# ====================


@admin.route("/payments")
@login_required
@admin_required
def payments():
    """Payment management page"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filters
    status = request.args.get("status")
    method = request.args.get("method")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    search = request.args.get("search")

    query = Payment.query.join(Booking).join(User)

    if status:
        query = query.filter_by(status=status)

    if method:
        query = query.filter_by(payment_method=method)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Payment.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Payment.created_at <= date_to_obj)
        except ValueError:
            pass

    if search:
        query = query.filter(
            (Payment.transaction_id.ilike(f"%{search}%"))
            | (User.username.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
        )

    payments = query.order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    statuses = ["pending", "completed", "failed", "refunded"]
    methods = ["mpesa", "card", "bank_transfer"]

    # Payment statistics
    total_revenue = (
        db.session.query(db.func.sum(Payment.amount))
        .filter(Payment.status == "completed")
        .scalar()
        or 0
    )

    pending_payments = (
        db.session.query(db.func.count(Payment.id))
        .filter(Payment.status == "pending")
        .scalar()
        or 0
    )

    return render_template(
        "admin/payments.html",
        payments=payments,
        statuses=statuses,
        methods=methods,
        total_revenue=total_revenue,
        pending_payments=pending_payments,
        filters=request.args,
    )


@admin.route("/payments/<int:payment_id>")
@login_required
@admin_required
def payment_detail(payment_id):
    """Get payment details"""
    payment = Payment.query.get_or_404(payment_id)

    # Get related booking and user info
    booking = Booking.query.get(payment.booking_id)
    user = User.query.get(payment.user_id) if payment.user_id else None

    # Get refund info if applicable
    refunds = Payment.query.filter_by(parent_payment_id=payment_id, type="refund").all()

    return render_template(
        "admin/payment_detail.html",
        payment=payment,
        booking=booking,
        user=user,
        refunds=refunds,
    )


@admin.route("/payments/<int:payment_id>/update-status", methods=["POST"])
@login_required
@admin_required
def update_payment_status(payment_id):
    """Update payment status"""
    payment = Payment.query.get_or_404(payment_id)
    data = request.get_json()

    new_status = data.get("status")
    notes = data.get("notes", "")

    if new_status not in ["pending", "completed", "failed", "refunded"]:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    old_status = payment.status
    payment.status = new_status
    payment.notes = notes

    if new_status == "completed":
        payment.completed_at = datetime.utcnow()

        # Update booking status if applicable
        booking = Booking.query.get(payment.booking_id)
        if booking and booking.status == "pending":
            booking.status = "confirmed"
            booking.confirmed_at = datetime.utcnow()

    log_admin_action(
        "update_payment_status",
        "payment",
        payment_id,
        {"old_status": old_status, "new_status": new_status, "notes": notes},
    )

    db.session.commit()

    # Notify user
    user = User.query.get(payment.user_id)
    if user and user.device_token:
        PushNotificationService.send_fcm_notification(
            user.device_token,
            "Payment Status Updated",
            f"Your payment #{payment.transaction_id} is now {new_status}",
            {
                "type": "payment_status_updated",
                "payment_id": payment.id,
                "status": new_status,
            },
        )

    return jsonify(
        {
            "success": True,
            "message": "Payment status updated",
            "payment": {
                "id": payment.id,
                "status": payment.status,
                "transaction_id": payment.transaction_id,
            },
        }
    )


@admin.route("/payments/<int:payment_id>/refund", methods=["POST"])
@login_required
@admin_required
def refund_payment(payment_id):
    """Process refund"""
    payment = Payment.query.get_or_404(payment_id)
    data = request.get_json()

    if payment.status != "completed":
        return jsonify(
            {"success": False, "error": "Only completed payments can be refunded"}
        ), 400

    amount = data.get("amount", payment.amount)
    reason = data.get("reason", "Admin refund")

    if amount > payment.amount:
        return jsonify(
            {"success": False, "error": "Refund amount cannot exceed original payment"}
        ), 400

    # Create refund record
    refund = Payment(
        user_id=payment.user_id,
        booking_id=payment.booking_id,
        amount=amount * -1,  # Negative amount for refund
        currency=payment.currency,
        payment_method=payment.payment_method,
        type="refund",
        status="completed",
        transaction_id=f"REFUND_{payment.transaction_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        notes=f"Refund for {payment.transaction_id}: {reason}",
        parent_payment_id=payment_id,
        metadata={
            "refund_reason": reason,
            "refunded_by": current_user.id,
            "original_amount": payment.amount,
            "refund_amount": amount,
        },
    )

    # Update original payment status
    payment.status = "refunded"
    payment.refunded_at = datetime.utcnow()
    payment.refund_amount = amount

    db.session.add(refund)

    log_admin_action(
        "process_refund",
        "payment",
        payment_id,
        {"refund_amount": amount, "reason": reason},
    )

    db.session.commit()

    # Notify user
    user = User.query.get(payment.user_id)
    if user:
        PushNotificationService.send_email_notification(
            user.email,
            "Payment Refund Processed",
            "payment_refunded",
            {
                "username": user.username,
                "refund_amount": amount,
                "currency": payment.currency,
                "transaction_id": payment.transaction_id,
                "refund_reason": reason,
            },
        )

    return jsonify(
        {
            "success": True,
            "message": f"Refund of {amount} {payment.currency} processed successfully",
            "refund": {
                "id": refund.id,
                "transaction_id": refund.transaction_id,
                "amount": amount,
                "currency": payment.currency,
            },
        }
    )


# ====================
# SUPPORT MANAGEMENT
# ====================


@admin.route("/support")
@login_required
@admin_required
def support_tickets():
    """Support tickets management"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filters
    status = request.args.get("status")
    priority = request.args.get("priority")
    category = request.args.get("category")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = SupportTicket.query.join(User)

    if status:
        query = query.filter_by(status=status)

    if priority:
        query = query.filter_by(priority=priority)

    if category:
        query = query.filter_by(category=category)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(SupportTicket.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(SupportTicket.created_at <= date_to_obj)
        except ValueError:
            pass

    tickets = query.order_by(
        SupportTicket.priority.desc(), SupportTicket.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    # Statistics
    open_tickets = SupportTicket.query.filter_by(status="open").count()
    high_priority = SupportTicket.query.filter_by(
        status="open", priority="high"
    ).count()

    categories = db.session.query(SupportTicket.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]

    return render_template(
        "admin/support.html",
        tickets=tickets,
        categories=categories,
        open_tickets=open_tickets,
        high_priority=high_priority,
        filters=request.args,
    )


@admin.route("/support/<int:ticket_id>")
@login_required
@admin_required
def support_ticket_detail(ticket_id):
    """Get support ticket details"""
    ticket = SupportTicket.query.get_or_404(ticket_id)

    # Get ticket replies
    replies = (
        SupportTicket.query.filter_by(parent_ticket_id=ticket_id)
        .order_by(SupportTicket.created_at.asc())
        .all()
    )

    # Get user info
    user = User.query.get(ticket.user_id)

    return render_template(
        "admin/ticket_detail.html", ticket=ticket, replies=replies, user=user
    )


@admin.route("/support/<int:ticket_id>/update", methods=["POST"])
@login_required
@admin_required
def update_support_ticket(ticket_id):
    """Update support ticket"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    data = request.get_json()

    action = data.get("action")  # reply, update_status, assign
    notes = data.get("notes", "")

    if action == "reply":
        # Create reply ticket
        reply = SupportTicket(
            user_id=current_user.id,
            parent_ticket_id=ticket_id,
            subject=f"Re: {ticket.subject}",
            message=notes,
            category=ticket.category,
            priority=ticket.priority,
            status="closed",  # Replies are automatically closed
            type="reply",
            assigned_to=current_user.id,
        )

        db.session.add(reply)

        # Update original ticket status if needed
        if ticket.status == "open":
            ticket.status = "in_progress"
            ticket.assigned_to = current_user.id

        log_admin_action(
            "reply_to_ticket", "support_ticket", ticket_id, {"reply_length": len(notes)}
        )

        # Notify user
        user = User.query.get(ticket.user_id)
        if user and user.device_token:
            PushNotificationService.send_fcm_notification(
                user.device_token,
                "New Reply to Your Support Ticket",
                f"Admin has replied to your ticket: {ticket.subject}",
                {
                    "type": "support_ticket_reply",
                    "ticket_id": ticket.id,
                    "ticket_subject": ticket.subject,
                },
            )

        message = "Reply sent successfully"

    elif action == "update_status":
        new_status = data.get("status")
        if new_status not in ["open", "in_progress", "closed"]:
            return jsonify({"success": False, "error": "Invalid status"}), 400

        old_status = ticket.status
        ticket.status = new_status

        if new_status == "closed":
            ticket.resolved_at = datetime.utcnow()
            ticket.resolved_by = current_user.id

        log_admin_action(
            "update_ticket_status",
            "support_ticket",
            ticket_id,
            {"old_status": old_status, "new_status": new_status},
        )

        message = "Ticket status updated"

    elif action == "assign":
        assign_to = data.get("assign_to")
        if assign_to:
            ticket.assigned_to = assign_to
            log_admin_action(
                "assign_ticket", "support_ticket", ticket_id, {"assigned_to": assign_to}
            )
            message = "Ticket assigned"
        else:
            return jsonify(
                {"success": False, "error": "No user specified for assignment"}
            ), 400

    else:
        return jsonify({"success": False, "error": "Invalid action"}), 400

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": message,
            "ticket": {
                "id": ticket.id,
                "status": ticket.status,
                "assigned_to": ticket.assigned_to,
            },
        }
    )


# ====================
# ANNOUNCEMENTS
# ====================


@admin.route("/announcements")
@login_required
@admin_required
def announcements():
    """Announcements management"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filters
    status = request.args.get("status")  # active, scheduled, expired
    audience = request.args.get("audience")

    query = Announcement.query

    now = datetime.utcnow()

    if status == "active":
        query = query.filter(
            Announcement.is_active == True,
            Announcement.publish_at <= now,
            Announcement.expire_at > now,
        )
    elif status == "scheduled":
        query = query.filter(Announcement.publish_at > now)
    elif status == "expired":
        query = query.filter(Announcement.expire_at <= now)

    if audience:
        query = query.filter(Announcement.audience == audience)

    announcements = query.order_by(Announcement.publish_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "admin/announcements.html", announcements=announcements, filters=request.args
    )


@admin.route("/announcements/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_announcement():
    """Create new announcement"""
    form = AnnouncementForm()

    if form.validate_on_submit():
        announcement = Announcement(
            title=form.title.data,
            content=form.content.data,
            audience=form.audience.data,
            priority=form.priority.data,
            is_active=form.is_active.data,
            publish_at=form.publish_at.data or datetime.utcnow(),
            expire_at=form.expire_at.data,
            created_by=current_user.id,
        )

        db.session.add(announcement)
        db.session.commit()

        log_admin_action(
            "create_announcement",
            "announcement",
            announcement.id,
            {"title": announcement.title, "audience": announcement.audience},
        )

        # Send push notifications if immediate
        if announcement.is_active and announcement.publish_at <= datetime.utcnow():
            PushNotificationService.broadcast_notification(
                announcement.audience,
                announcement.title,
                announcement.content[:100],
                {"type": "announcement", "announcement_id": announcement.id},
            )

        flash("Announcement created successfully!", "success")
        return redirect(url_for("admin.announcements"))

    return render_template("admin/create_announcement.html", form=form)


@admin.route("/announcements/<int:announcement_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_announcement(announcement_id):
    """Edit announcement"""
    announcement = Announcement.query.get_or_404(announcement_id)
    form = AnnouncementForm(obj=announcement)

    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.content = form.content.data
        announcement.audience = form.audience.data
        announcement.priority = form.priority.data
        announcement.is_active = form.is_active.data
        announcement.publish_at = form.publish_at.data
        announcement.expire_at = form.expire_at.data
        announcement.updated_at = datetime.utcnow()

        log_admin_action(
            "update_announcement",
            "announcement",
            announcement_id,
            {"title": announcement.title},
        )

        db.session.commit()

        flash("Announcement updated successfully!", "success")
        return redirect(url_for("admin.announcements"))

    return render_template(
        "admin/edit_announcement.html", form=form, announcement=announcement
    )


@admin.route("/announcements/<int:announcement_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_announcement(announcement_id):
    """Delete announcement"""
    announcement = Announcement.query.get_or_404(announcement_id)

    log_admin_action(
        "delete_announcement",
        "announcement",
        announcement_id,
        {"title": announcement.title},
    )

    db.session.delete(announcement)
    db.session.commit()

    return jsonify({"success": True, "message": "Announcement deleted successfully"})


# ====================
# PLATFORM SETTINGS
# ====================


@admin.route("/settings")
@login_required
@super_admin_required
def platform_settings():
    """Platform settings management"""
    settings = PlatformSetting.query.all()

    # Group settings by category
    grouped_settings = {}
    for setting in settings:
        if setting.category not in grouped_settings:
            grouped_settings[setting.category] = []
        grouped_settings[setting.category].append(setting)

    return render_template("admin/settings.html", settings=grouped_settings)


@admin.route("/settings/update", methods=["POST"])
@login_required
@super_admin_required
def update_settings():
    """Update platform settings"""
    data = request.get_json()

    for key, value in data.items():
        setting = PlatformSetting.query.filter_by(key=key).first()
        if setting:
            old_value = setting.value
            setting.value = value

            log_admin_action(
                "update_setting",
                "platform_setting",
                setting.id,
                {"key": key, "old_value": old_value, "new_value": value},
            )

    db.session.commit()

    return jsonify({"success": True, "message": "Settings updated successfully"})


@admin.route("/settings/add", methods=["POST"])
@login_required
@super_admin_required
def add_setting():
    """Add new platform setting"""
    data = request.get_json()

    key = data.get("key")
    value = data.get("value")
    category = data.get("category", "general")
    data_type = data.get("data_type", "string")
    description = data.get("description", "")

    if not key or not value:
        return jsonify({"success": False, "error": "Key and value are required"}), 400

    # Check if key already exists
    existing = PlatformSetting.query.filter_by(key=key).first()
    if existing:
        return jsonify({"success": False, "error": "Setting key already exists"}), 400

    setting = PlatformSetting(
        key=key,
        value=value,
        category=category,
        data_type=data_type,
        description=description,
    )

    db.session.add(setting)
    db.session.commit()

    log_admin_action(
        "add_setting",
        "platform_setting",
        setting.id,
        {"key": key, "value": value, "category": category},
    )

    return jsonify(
        {
            "success": True,
            "message": "Setting added successfully",
            "setting": {"id": setting.id, "key": setting.key, "value": setting.value},
        }
    )


# ====================
# AUDIT LOGS
# ====================


@admin.route("/audit-logs")
@login_required
@super_admin_required
def audit_logs():
    """View admin audit logs"""
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Filters
    action = request.args.get("action")
    admin_id = request.args.get("admin_id")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = AdminAuditLog.query.join(User, AdminAuditLog.admin_id == User.id)

    if action:
        query = query.filter_by(action=action)

    if admin_id:
        query = query.filter_by(admin_id=admin_id)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(AdminAuditLog.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(AdminAuditLog.created_at <= date_to_obj)
        except ValueError:
            pass

    logs = query.order_by(AdminAuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get distinct actions for filter dropdown
    actions = db.session.query(AdminAuditLog.action).distinct().all()
    actions = [act[0] for act in actions]

    # Get admin users
    admins = User.query.filter_by(user_type="admin").all()

    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        actions=actions,
        admins=admins,
        filters=request.args,
    )


# ====================
# DATA EXPORT
# ====================


@admin.route("/export")
@login_required
@admin_required
def export_data_page():
    """Data export page"""
    export_types = [
        {"id": "users", "name": "Users", "description": "Export all user data"},
        {"id": "tutors", "name": "Tutors", "description": "Export tutor profiles"},
        {"id": "bookings", "name": "Bookings", "description": "Export booking history"},
        {"id": "payments", "name": "Payments", "description": "Export payment records"},
        {"id": "reviews", "name": "Reviews", "description": "Export tutor reviews"},
    ]

    return render_template("admin/export.html", export_types=export_types)


@admin.route("/export/<export_type>", methods=["POST"])
@login_required
@admin_required
def export_data_route(export_type):
    """Export data endpoint"""
    filters = request.get_json() or {}
    format = filters.pop("format", "csv")

    data = export_data(export_type, format, filters)

    if format == "csv":
        return send_file(
            BytesIO(data.encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{export_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
    elif format == "json":
        return send_file(
            BytesIO(data.encode()),
            mimetype="application/json",
            as_attachment=True,
            download_name=f"{export_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
    elif format == "excel":
        # For Excel export, you'd need to create an Excel file
        # This is a placeholder - implement with pandas or similar
        return jsonify(
            {"success": False, "error": "Excel export not implemented yet"}
        ), 501
    else:
        return jsonify({"success": False, "error": "Unsupported export format"}), 400


# ====================
# SYSTEM TOOLS
# ====================


@admin.route("/system/health")
@login_required
@super_admin_required
def system_health():
    """System health check"""
    health_data = {
        "database": check_database_health(),
        "cache": check_cache_health(),
        "storage": check_storage_health(),
        "email": check_email_health(),
        "sms": check_sms_health(),
    }

    return jsonify(
        {
            "success": True,
            "health": health_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@admin.route("/system/clear-cache", methods=["POST"])
@login_required
@super_admin_required
def clear_cache():
    """Clear system cache"""
    cache_type = request.json.get("type", "all")

    if cache_type == "all" or cache_type == "tutors":
        # Clear tutor cache (implement based on your caching system)
        pass

    if cache_type == "all" or cache_type == "users":
        # Clear user cache
        pass

    log_admin_action("clear_cache", "system", None, {"cache_type": cache_type})

    return jsonify(
        {"success": True, "message": f"{cache_type} cache cleared successfully"}
    )


@admin.route("/system/backup", methods=["POST"])
@login_required
@super_admin_required
def create_backup():
    """Create database backup"""
    backup_type = request.json.get("type", "database")  # database, files, full

    try:
        # Implement backup logic here
        # This would typically use your database backup tool
        backup_file = perform_backup(backup_type)

        log_admin_action(
            "create_backup",
            "system",
            None,
            {"backup_type": backup_type, "backup_file": backup_file},
        )

        return jsonify(
            {
                "success": True,
                "message": f"{backup_type} backup created successfully",
                "backup_file": backup_file,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"Backup failed: {str(e)}"}), 500


# ====================
# HELPER FUNCTIONS
# ====================


def check_database_health():
    """Check database connection and performance"""
    try:
        start_time = datetime.utcnow()
        result = db.session.execute("SELECT 1").fetchone()
        end_time = datetime.utcnow()

        response_time = (end_time - start_time).total_seconds() * 1000

        # Get some statistics
        total_users = User.query.count()
        total_bookings = Booking.query.count()

        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "total_users": total_users,
            "total_bookings": total_bookings,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_cache_health():
    """Check cache system health"""
    # Implement based on your caching system (Redis, Memcached, etc.)
    return {"status": "unknown", "message": "Cache health check not implemented"}


def check_storage_health():
    """Check storage system health"""
    # Implement based on your storage system
    return {"status": "unknown", "message": "Storage health check not implemented"}


def check_email_health():
    """Check email service health"""
    # Implement email service health check
    return {"status": "unknown", "message": "Email health check not implemented"}


def check_sms_health():
    """Check SMS service health"""
    # Implement SMS service health check
    return {"status": "unknown", "message": "SMS health check not implemented"}


def perform_backup(backup_type):
    """Perform system backup"""
    # Implement backup logic
    # This would typically:
    # 1. Dump database to SQL file
    # 2. Archive uploaded files
    # 3. Upload to cloud storage
    # 4. Return backup file path/URL

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{backup_type}_{timestamp}.zip"


# admin.py (continued from the previous code)

# ====================
# CONFIGURATION IMPORT
# ====================

from config import ProductionConfig, DevelopmentConfig, TestingConfig

# ====================
# CONFIGURATION ROUTES
# ====================


@admin.route("/system/config")
@login_required
@super_admin_required
def view_config():
    """View current configuration (read-only, no sensitive data)"""
    # Only show non-sensitive configuration
    safe_config = {
        "app_name": current_app.config.get("APP_NAME"),
        "app_version": current_app.config.get("APP_VERSION"),
        "debug": current_app.config.get("DEBUG"),
        "testing": current_app.config.get("TESTING"),
        "database": {
            "pool_size": current_app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}).get(
                "pool_size"
            ),
            "max_overflow": current_app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}).get(
                "max_overflow"
            ),
        },
        "upload": {
            "max_content_length": current_app.config.get("MAX_CONTENT_LENGTH"),
            "upload_folder": current_app.config.get("UPLOAD_FOLDER"),
        },
        "platform": {
            "commission_percentage": current_app.config.get(
                "PLATFORM_COMMISSION_PERCENTAGE"
            ),
            "minimum_withdrawal": current_app.config.get("MINIMUM_WITHDRAWAL_AMOUNT"),
            "max_booking_hours": current_app.config.get("MAX_BOOKING_HOURS"),
        },
        "cache": {
            "type": current_app.config.get("CACHE_TYPE"),
            "default_timeout": current_app.config.get("CACHE_DEFAULT_TIMEOUT"),
        },
        "rate_limit": {
            "enabled": current_app.config.get("RATELIMIT_ENABLED"),
            "default": current_app.config.get("RATELIMIT_DEFAULT"),
        },
        "environment": os.environ.get("FLASK_ENV", "development"),
    }

    return jsonify({"success": True, "config": safe_config})


@admin.route("/system/config/reload", methods=["POST"])
@login_required
@super_admin_required
def reload_config():
    """Reload configuration from environment variables"""
    try:
        # This would reload configuration in a production environment
        # For Flask, you might need to restart the app or use a config reloader

        log_admin_action(
            "reload_config",
            "system",
            None,
            {"reload_time": datetime.utcnow().isoformat()},
        )

        return jsonify(
            {
                "success": True,
                "message": "Configuration reload triggered. App restart may be required.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "error": f"Failed to reload config: {str(e)}"}
        ), 500


# ====================
# ENVIRONMENT SWITCHING (Development Only)
# ====================


@admin.route("/system/switch-env", methods=["POST"])
@login_required
@super_admin_required
def switch_environment():
    """Switch between development/testing environments (Development only)"""
    # SECURITY: Only allow in development mode
    if not current_app.debug:
        return jsonify(
            {
                "success": False,
                "error": "Environment switching only available in development mode",
            }
        ), 403

    data = request.get_json()
    new_env = data.get("environment", "development")

    valid_envs = ["development", "testing", "staging"]
    if new_env not in valid_envs:
        return jsonify(
            {
                "success": False,
                "error": f"Invalid environment. Must be one of: {', '.join(valid_envs)}",
            }
        ), 400

    # In a real application, you would:
    # 1. Update environment variables
    # 2. Reload configuration
    # 3. Reinitialize database connections, etc.

    log_admin_action(
        "switch_environment",
        "system",
        None,
        {"old_env": os.environ.get("FLASK_ENV"), "new_env": new_env},
    )

    return jsonify(
        {
            "success": True,
            "message": f"Environment switched to {new_env}. App restart required.",
            "environment": new_env,
        }
    )


# ====================
# FINAL EXPORT
# ====================


def init_admin(app):
    """Initialize admin blueprint with the app"""
    app.register_blueprint(admin)

    # Create necessary directories
    for directory in [app.config["UPLOAD_FOLDER"], "/tmp/edututor_exports"]:
        os.makedirs(directory, exist_ok=True)

    # Initialize admin user if not exists
    with app.app_context():
        from app.models import User

        admin_email = app.config.get("ADMIN_EMAIL")

        if admin_email and not User.query.filter_by(email=admin_email).first():
            admin_user = User(
                username="admin",
                email=admin_email,
                user_type="super_admin",
                is_active=True,
                is_verified=True,
                is_super_admin=True,
            )
            # Set a default password (should be changed on first login)
            admin_user.set_password("ChangeMe123!")

            db.session.add(admin_user)
            db.session.commit()

            app.logger.info(f"Default admin user created: {admin_email}")
