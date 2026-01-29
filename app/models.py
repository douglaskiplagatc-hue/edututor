from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# USER
# =========================
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    phone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # student | tutor | parent

    profile_picture = db.Column(db.String(200), default="default-avatar.png")
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # ---------- Relationships ----------

    # 1–1 (User → Tutor)
    tutor_profile = db.relationship(
        "Tutor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Student bookings
    bookings_as_student = db.relationship(
        "Booking",
        foreign_keys="Booking.student_id",
        back_populates="student",
        lazy="dynamic",
    )

    # Messaging
    messages_sent = db.relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        lazy="dynamic",
    )

    messages_received = db.relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        back_populates="receiver",
        lazy="dynamic",
    )

    # Reviews written
    reviews_written = db.relationship(
        "Review",
        back_populates="author",
        lazy="dynamic",
    )

    # Notifications
    notifications = db.relationship(
        "Notification",
        back_populates="user",
        lazy="dynamic",
    )

    # ---------- Auth helpers ----------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# =========================
# TUTOR
# =========================
class Tutor(db.Model):
    __tablename__ = "tutors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )

    full_name = db.Column(db.String(100), nullable=False)
    qualifications = db.Column(db.Text, nullable=False)
    subjects = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(50), nullable=False)

    experience_years = db.Column(db.Integer, default=0)
    hourly_rate = db.Column(db.Integer, nullable=False)

    availability = db.Column(db.String(100), nullable=False)
    teaching_mode = db.Column(db.String(50), nullable=False)
    bio = db.Column(db.Text, nullable=False)

    rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)

    is_featured = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ---------- Relationships ----------

    user = db.relationship(
        "User",
        back_populates="tutor_profile",
    )

    bookings = db.relationship(
        "Booking",
        back_populates="tutor",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    reviews = db.relationship(
        "Review",
        back_populates="tutor",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    schedules = db.relationship(
        "Schedule",
        back_populates="tutor",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Tutor {self.full_name}>"


# =========================
# BOOKING
# =========================
class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey("tutors.id"), nullable=False)

    subject = db.Column(db.String(100), nullable=False)
    hours = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, nullable=False)

    schedule_date = db.Column(db.Date, nullable=False)
    schedule_time = db.Column(db.String(50), nullable=False)

    status = db.Column(db.String(20), default="pending")
    payment_status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---------- Relationships ----------

    student = db.relationship(
        "User",
        foreign_keys=[student_id],
        back_populates="bookings_as_student",
    )

    tutor = db.relationship(
        "Tutor",
        foreign_keys=[tutor_id],
        back_populates="bookings",
    )

    payments = db.relationship(
        "Payment",
        back_populates="booking",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    review = db.relationship(
        "Review",
        back_populates="booking",
        uselist=False,
    )

    def __repr__(self):
        return f"<Booking {self.id}>"


# =========================
# REVIEW
# =========================
class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)

    tutor_id = db.Column(db.Integer, db.ForeignKey("tutors.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tutor = db.relationship("Tutor", back_populates="reviews")
    author = db.relationship("User", back_populates="reviews_written")
    booking = db.relationship("Booking", back_populates="review")

    def __repr__(self):
        return f"<Review {self.id}>"


# =========================
# MESSAGE
# =========================
class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"))
    content = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="messages_sent",
    )

    receiver = db.relationship(
        "User",
        foreign_keys=[receiver_id],
        back_populates="messages_received",
    )

    booking = db.relationship("Booking")

    def __repr__(self):
        return f"<Message {self.id}>"


# =========================
# PAYMENT
# =========================
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    mpesa_code = db.Column(db.String(50), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship("Booking", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id}>"


# =========================
# SCHEDULE
# =========================
class Schedule(db.Model):
    __tablename__ = "schedules"

    id = db.Column(db.Integer, primary_key=True)
    tutor_id = db.Column(db.Integer, db.ForeignKey("tutors.id"), nullable=False)

    day_of_week = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    tutor = db.relationship("Tutor", back_populates="schedules")

    def __repr__(self):
        return f"<Schedule {self.id}>"


# =========================
# NOTIFICATION
# =========================
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id}>"
class AdminAuditLog(db.Model):
    """Track admin actions"""
    __tablename__ = 'admin_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))  # user, tutor, booking, payment
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('User', backref='audit_logs')

class SupportTicket(db.Model):
    """Customer support tickets"""
    __tablename__ = 'support_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # technical, billing, account, general
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolution = db.Column(db.Text)
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='support_tickets')
    admin = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')
    messages = db.relationship('TicketMessage', backref='ticket', lazy='dynamic')

class TicketMessage(db.Model):
    """Support ticket messages"""
    __tablename__ = 'ticket_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_tickets.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)  # Internal admin notes
    attachments = db.Column(db.Text)  # JSON list of file paths
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', backref='ticket_messages')

class PlatformSetting(db.Model):
    """Platform configuration settings"""
    __tablename__ = 'platform_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, float, boolean, json
    category = db.Column(db.String(50), default='general')
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    admin = db.relationship('User', backref='settings_updated')

class Announcement(db.Model):
    """Platform announcements/banners"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(30), default='info')  # info, warning, success, danger
    target_audience = db.Column(db.String(50), default='all')  # all, students, tutors, specific
    target_ids = db.Column(db.Text)  # JSON array of user IDs if specific
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    creator = db.relationship('User', backref='announcements')