# forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectField,
    IntegerField,
    FloatField,
    DateField,
    DateTimeField,
    BooleanField,
    FileField,
    HiddenField,
    RadioField,
    SelectMultipleField,
    DecimalField,
    EmailField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Optional,
    NumberRange,
    ValidationError,
    URL,
    Regexp,
)
from wtforms.widgets import TextArea, CheckboxInput, ListWidget
from flask_wtf.file import FileAllowed, FileRequired
from datetime import datetime
import re


# Custom validators
def phone_validator(form, field):
    """Validate Kenyan phone number"""
    phone_pattern = r"^(?:\+254|0)[17]\d{8}$"
    if not re.match(phone_pattern, field.data):
        raise ValidationError(
            "Please enter a valid Kenyan phone number (e.g., +254712345678 or 0712345678)"
        )


def id_number_validator(form, field):
    """Validate Kenyan ID number"""
    if field.data and len(field.data) not in [7, 8]:
        raise ValidationError("ID number must be 7 or 8 digits")


def password_strength_validator(form, field):
    """Validate password strength"""
    password = field.data
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character")


def future_date_validator(form, field):
    """Validate that date is in the future"""
    if field.data and field.data < datetime.now().date():
        raise ValidationError("Date must be in the future")


def hourly_rate_validator(form, field):
    """Validate hourly rate"""
    if field.data < 100:
        raise ValidationError("Hourly rate must be at least KSh 100")
    if field.data > 10000:
        raise ValidationError("Hourly rate cannot exceed KSh 10,000")


# Login Forms
class LoginForm(FlaskForm):
    """User login form"""

    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    password = PasswordField(
        "Password", validators=[DataRequired(message="Password is required")]
    )
    remember = BooleanField("Remember me")


class AdminLoginForm(FlaskForm):
    """Admin login form"""

    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    password = PasswordField(
        "Password", validators=[DataRequired(message="Password is required")]
    )
    otp = StringField(
        "OTP (if 2FA enabled)",
        validators=[
            Optional(),
            Length(min=6, max=6, message="OTP must be 6 digits"),
            Regexp(r"^\d{6}$", message="OTP must contain only digits"),
        ],
    )


# Registration Forms
class StudentRegistrationForm(FlaskForm):
    """Student registration form"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(
                min=3, max=50, message="Username must be between 3 and 50 characters"
            ),
            Regexp(
                r"^[a-zA-Z0-9_]+$",
                message="Username can only contain letters, numbers, and underscores",
            ),
        ],
    )
    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[DataRequired(message="Phone number is required"), phone_validator],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required"),
            password_strength_validator,
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
        ],
    )
    grade_level = SelectField(
        "Grade Level",
        choices=[
            ("", "Select Grade Level"),
            ("primary", "Primary School"),
            ("form_1-2", "Form 1-2"),
            ("form_3-4", "Form 3-4"),
            ("college", "College/University"),
            ("adult", "Adult Learner"),
        ],
        validators=[DataRequired(message="Grade level is required")],
    )
    subjects = SelectMultipleField(
        "Subjects of Interest",
        choices=[
            ("mathematics", "Mathematics"),
            ("english", "English"),
            ("kiswahili", "Kiswahili"),
            ("physics", "Physics"),
            ("chemistry", "Chemistry"),
            ("biology", "Biology"),
            ("history", "History"),
            ("geography", "Geography"),
            ("business", "Business Studies"),
            ("computer", "Computer Studies"),
            ("french", "French"),
            ("german", "German"),
            ("music", "Music"),
            ("art", "Art & Design"),
        ],
        validators=[DataRequired(message="Select at least one subject")],
    )
    location = StringField(
        "Location", validators=[DataRequired(message="Location is required")]
    )
    terms = BooleanField(
        "I agree to the Terms and Conditions",
        validators=[DataRequired(message="You must agree to the terms and conditions")],
    )


class TutorRegistrationForm(FlaskForm):
    """Tutor registration form"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(
                min=3, max=50, message="Username must be between 3 and 50 characters"
            ),
            Regexp(
                r"^[a-zA-Z0-9_]+$",
                message="Username can only contain letters, numbers, and underscores",
            ),
        ],
    )
    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[DataRequired(message="Phone number is required"), phone_validator],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required"),
            password_strength_validator,
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
        ],
    )
    id_number = StringField(
        "National ID Number",
        validators=[
            DataRequired(message="ID number is required"),
            Length(min=7, max=8, message="ID number must be 7 or 8 digits"),
            Regexp(r"^\d+$", message="ID number must contain only digits"),
        ],
    )
    date_of_birth = DateField(
        "Date of Birth", validators=[DataRequired(message="Date of birth is required")]
    )
    gender = SelectField(
        "Gender",
        choices=[
            ("", "Select Gender"),
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not_to_say", "Prefer not to say"),
        ],
        validators=[DataRequired(message="Gender is required")],
    )

    # Education
    highest_education = SelectField(
        "Highest Education Level",
        choices=[
            ("", "Select Education Level"),
            ("high_school", "High School"),
            ("certificate", "Certificate"),
            ("diploma", "Diploma"),
            ("bachelors", "Bachelor's Degree"),
            ("masters", "Master's Degree"),
            ("phd", "PhD"),
            ("professor", "Professor"),
        ],
        validators=[DataRequired(message="Education level is required")],
    )
    institution = StringField(
        "Institution", validators=[DataRequired(message="Institution name is required")]
    )
    year_of_graduation = IntegerField(
        "Year of Graduation",
        validators=[
            DataRequired(message="Year of graduation is required"),
            NumberRange(
                min=1900, max=datetime.now().year, message="Enter a valid year"
            ),
        ],
    )

    # Tutoring details
    subjects = SelectMultipleField(
        "Subjects You Teach",
        choices=[
            ("mathematics", "Mathematics"),
            ("english", "English"),
            ("kiswahili", "Kiswahili"),
            ("physics", "Physics"),
            ("chemistry", "Chemistry"),
            ("biology", "Biology"),
            ("history", "History"),
            ("geography", "Geography"),
            ("business", "Business Studies"),
            ("computer", "Computer Studies"),
            ("french", "French"),
            ("german", "German"),
            ("music", "Music"),
            ("art", "Art & Design"),
        ],
        validators=[DataRequired(message="Select at least one subject")],
    )
    education_levels = SelectMultipleField(
        "Education Levels You Teach",
        choices=[
            ("primary", "Primary School"),
            ("form_1-2", "Form 1-2"),
            ("form_3-4", "Form 3-4"),
            ("college", "College/University"),
            ("adult", "Adult Learner"),
        ],
        validators=[DataRequired(message="Select at least one education level")],
    )
    hourly_rate = DecimalField(
        "Hourly Rate (KSh)",
        places=2,
        validators=[
            DataRequired(message="Hourly rate is required"),
            NumberRange(
                min=100,
                max=10000,
                message="Hourly rate must be between KSh 100 and KSh 10,000",
            ),
            hourly_rate_validator,
        ],
    )
    experience_years = IntegerField(
        "Years of Tutoring Experience",
        validators=[
            DataRequired(message="Experience is required"),
            NumberRange(
                min=0, max=50, message="Experience must be between 0 and 50 years"
            ),
        ],
    )

    # Location and availability
    location = StringField(
        "Location", validators=[DataRequired(message="Location is required")]
    )
    available_days = SelectMultipleField(
        "Available Days",
        choices=[
            ("monday", "Monday"),
            ("tuesday", "Tuesday"),
            ("wednesday", "Wednesday"),
            ("thursday", "Thursday"),
            ("friday", "Friday"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
        ],
        validators=[DataRequired(message="Select at least one available day")],
    )
    available_times = SelectMultipleField(
        "Available Times",
        choices=[
            ("morning", "Morning (8AM - 12PM)"),
            ("afternoon", "Afternoon (12PM - 5PM)"),
            ("evening", "Evening (5PM - 9PM)"),
            ("weekend", "Weekend"),
        ],
        validators=[DataRequired(message="Select at least one available time")],
    )

    # Profile
    bio = TextAreaField(
        "Bio/Introduction",
        validators=[
            DataRequired(message="Please write a short bio"),
            Length(
                min=50, max=1000, message="Bio must be between 50 and 1000 characters"
            ),
        ],
    )
    teaching_approach = TextAreaField(
        "Teaching Approach",
        validators=[
            DataRequired(message="Please describe your teaching approach"),
            Length(
                min=50,
                max=1000,
                message="Teaching approach must be between 50 and 1000 characters",
            ),
        ],
    )

    # Documents
    id_document = FileField(
        "ID Document (PDF/Image)",
        validators=[
            FileRequired(message="ID document is required"),
            FileAllowed(
                ["jpg", "jpeg", "png", "pdf"], "Images (JPG, PNG) or PDF only!"
            ),
        ],
    )
    education_certificate = FileField(
        "Education Certificate (PDF/Image)",
        validators=[
            FileRequired(message="Education certificate is required"),
            FileAllowed(
                ["jpg", "jpeg", "png", "pdf"], "Images (JPG, PNG) or PDF only!"
            ),
        ],
    )
    profile_picture = FileField(
        "Profile Picture (Optional)",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Images only!")],
    )

    # References
    reference_name = StringField(
        "Reference Name",
        validators=[DataRequired(message="Reference name is required")],
    )
    reference_phone = StringField(
        "Reference Phone",
        validators=[
            DataRequired(message="Reference phone is required"),
            phone_validator,
        ],
    )
    reference_relationship = StringField(
        "Relationship", validators=[DataRequired(message="Relationship is required")]
    )

    terms = BooleanField(
        "I agree to the Terms and Conditions",
        validators=[DataRequired(message="You must agree to the terms and conditions")],
    )


# User Profile Forms
class UserProfileForm(FlaskForm):
    """User profile update form"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(
                min=3, max=50, message="Username must be between 3 and 50 characters"
            ),
            Regexp(
                r"^[a-zA-Z0-9_]+$",
                message="Username can only contain letters, numbers, and underscores",
            ),
        ],
    )
    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[DataRequired(message="Phone number is required"), phone_validator],
    )
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
        ],
    )
    profile_picture = FileField(
        "Profile Picture",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Images only!")],
    )
    bio = TextAreaField(
        "Bio",
        validators=[
            Optional(),
            Length(max=500, message="Bio cannot exceed 500 characters"),
        ],
    )
    location = StringField(
        "Location", validators=[DataRequired(message="Location is required")]
    )


class ChangePasswordForm(FlaskForm):
    """Change password form"""

    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Current password is required")],
    )
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required"),
            password_strength_validator,
        ],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password"),
            EqualTo("new_password", message="Passwords must match"),
        ],
    )


class ForgotPasswordForm(FlaskForm):
    """Forgot password form"""

    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )


class ResetPasswordForm(FlaskForm):
    """Reset password form"""

    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required"),
            password_strength_validator,
        ],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password"),
            EqualTo("new_password", message="Passwords must match"),
        ],
    )


# Tutor Profile Forms
class TutorProfileForm(FlaskForm):
    """Tutor profile update form"""

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
        ],
    )
    bio = TextAreaField(
        "Bio/Introduction",
        validators=[
            DataRequired(message="Please write a short bio"),
            Length(
                min=50, max=1000, message="Bio must be between 50 and 1000 characters"
            ),
        ],
    )
    teaching_approach = TextAreaField(
        "Teaching Approach",
        validators=[
            DataRequired(message="Please describe your teaching approach"),
            Length(
                min=50,
                max=1000,
                message="Teaching approach must be between 50 and 1000 characters",
            ),
        ],
    )
    subjects = SelectMultipleField(
        "Subjects You Teach",
        choices=[
            ("mathematics", "Mathematics"),
            ("english", "English"),
            ("kiswahili", "Kiswahili"),
            ("physics", "Physics"),
            ("chemistry", "Chemistry"),
            ("biology", "Biology"),
            ("history", "History"),
            ("geography", "Geography"),
            ("business", "Business Studies"),
            ("computer", "Computer Studies"),
            ("french", "French"),
            ("german", "German"),
            ("music", "Music"),
            ("art", "Art & Design"),
        ],
        validators=[DataRequired(message="Select at least one subject")],
    )
    education_levels = SelectMultipleField(
        "Education Levels You Teach",
        choices=[
            ("primary", "Primary School"),
            ("form_1-2", "Form 1-2"),
            ("form_3-4", "Form 3-4"),
            ("college", "College/University"),
            ("adult", "Adult Learner"),
        ],
        validators=[DataRequired(message="Select at least one education level")],
    )
    hourly_rate = DecimalField(
        "Hourly Rate (KSh)",
        places=2,
        validators=[
            DataRequired(message="Hourly rate is required"),
            NumberRange(
                min=100,
                max=10000,
                message="Hourly rate must be between KSh 100 and KSh 10,000",
            ),
            hourly_rate_validator,
        ],
    )
    experience_years = IntegerField(
        "Years of Tutoring Experience",
        validators=[
            DataRequired(message="Experience is required"),
            NumberRange(
                min=0, max=50, message="Experience must be between 0 and 50 years"
            ),
        ],
    )
    location = StringField(
        "Location", validators=[DataRequired(message="Location is required")]
    )
    available_days = SelectMultipleField(
        "Available Days",
        choices=[
            ("monday", "Monday"),
            ("tuesday", "Tuesday"),
            ("wednesday", "Wednesday"),
            ("thursday", "Thursday"),
            ("friday", "Friday"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
        ],
        validators=[DataRequired(message="Select at least one available day")],
    )
    available_times = SelectMultipleField(
        "Available Times",
        choices=[
            ("morning", "Morning (8AM - 12PM)"),
            ("afternoon", "Afternoon (12PM - 5PM)"),
            ("evening", "Evening (5PM - 9PM)"),
            ("weekend", "Weekend"),
        ],
        validators=[DataRequired(message="Select at least one available time")],
    )
    is_available = BooleanField("Available for New Students")
    profile_picture = FileField(
        "Profile Picture",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Images only!")],
    )
    resume = FileField(
        "Resume/CV (Optional)",
        validators=[
            Optional(),
            FileAllowed(["pdf", "doc", "docx"], "PDF or Word documents only!"),
        ],
    )


class TutorAvailabilityForm(FlaskForm):
    """Tutor availability schedule form"""

    monday_morning = BooleanField("Monday Morning")
    monday_afternoon = BooleanField("Monday Afternoon")
    monday_evening = BooleanField("Monday Evening")

    tuesday_morning = BooleanField("Tuesday Morning")
    tuesday_afternoon = BooleanField("Tuesday Afternoon")
    tuesday_evening = BooleanField("Tuesday Evening")

    wednesday_morning = BooleanField("Wednesday Morning")
    wednesday_afternoon = BooleanField("Wednesday Afternoon")
    wednesday_evening = BooleanField("Wednesday Evening")

    thursday_morning = BooleanField("Thursday Morning")
    thursday_afternoon = BooleanField("Thursday Afternoon")
    thursday_evening = BooleanField("Thursday Evening")

    friday_morning = BooleanField("Friday Morning")
    friday_afternoon = BooleanField("Friday Afternoon")
    friday_evening = BooleanField("Friday Evening")

    saturday_morning = BooleanField("Saturday Morning")
    saturday_afternoon = BooleanField("Saturday Afternoon")
    saturday_evening = BooleanField("Saturday Evening")

    sunday_morning = BooleanField("Sunday Morning")
    sunday_afternoon = BooleanField("Sunday Afternoon")
    sunday_evening = BooleanField("Sunday Evening")


# Booking Forms
class BookingForm(FlaskForm):
    """Create booking form"""

    tutor_id = HiddenField("Tutor ID", validators=[DataRequired()])
    subject = SelectField(
        "Subject", validators=[DataRequired(message="Subject is required")]
    )
    education_level = SelectField(
        "Education Level",
        choices=[
            ("primary", "Primary School"),
            ("form_1-2", "Form 1-2"),
            ("form_3-4", "Form 3-4"),
            ("college", "College/University"),
            ("adult", "Adult Learner"),
        ],
        validators=[DataRequired(message="Education level is required")],
    )
    topics = TextAreaField(
        "Topics to Cover",
        validators=[
            DataRequired(message="Please specify topics to cover"),
            Length(
                min=10, max=500, message="Topics must be between 10 and 500 characters"
            ),
        ],
    )
    duration_hours = IntegerField(
        "Duration (Hours)",
        validators=[
            DataRequired(message="Duration is required"),
            NumberRange(min=1, max=8, message="Duration must be between 1 and 8 hours"),
        ],
    )
    booking_date = DateField(
        "Preferred Date",
        validators=[DataRequired(message="Date is required"), future_date_validator],
    )
    preferred_time = SelectField(
        "Preferred Time",
        choices=[
            ("morning", "Morning (8AM - 12PM)"),
            ("afternoon", "Afternoon (12PM - 5PM)"),
            ("evening", "Evening (5PM - 9PM)"),
        ],
        validators=[DataRequired(message="Time is required")],
    )
    location_type = SelectField(
        "Location Type",
        choices=[
            ("online", "Online"),
            ("in_person", "In Person"),
            ("both", "Either is fine"),
        ],
        validators=[DataRequired(message="Location type is required")],
    )
    specific_location = StringField(
        "Specific Location (if in person)", validators=[Optional()]
    )
    special_requirements = TextAreaField(
        "Special Requirements",
        validators=[
            Optional(),
            Length(max=500, message="Requirements cannot exceed 500 characters"),
        ],
    )
    urgency = SelectField(
        "Urgency",
        choices=[
            ("normal", "Normal (Within 1 week)"),
            ("urgent", "Urgent (Within 3 days)"),
            ("emergency", "Emergency (Within 24 hours)"),
        ],
        default="normal",
    )


class BookingRescheduleForm(FlaskForm):
    """Reschedule booking form"""

    new_date = DateField(
        "New Date",
        validators=[
            DataRequired(message="New date is required"),
            future_date_validator,
        ],
    )
    new_time = SelectField(
        "New Time",
        choices=[
            ("morning", "Morning (8AM - 12PM)"),
            ("afternoon", "Afternoon (12PM - 5PM)"),
            ("evening", "Evening (5PM - 9PM)"),
        ],
        validators=[DataRequired(message="New time is required")],
    )
    reason = TextAreaField(
        "Reason for Rescheduling",
        validators=[
            DataRequired(message="Please provide a reason"),
            Length(
                min=10, max=500, message="Reason must be between 10 and 500 characters"
            ),
        ],
    )


class BookingCancellationForm(FlaskForm):
    """Cancel booking form"""

    reason = SelectField(
        "Cancellation Reason",
        choices=[
            ("schedule_conflict", "Schedule Conflict"),
            ("found_another_tutor", "Found Another Tutor"),
            ("financial_reasons", "Financial Reasons"),
            ("personal_reasons", "Personal Reasons"),
            ("dissatisfied_with_tutor", "Dissatisfied with Tutor"),
            ("other", "Other"),
        ],
        validators=[DataRequired(message="Reason is required")],
    )
    details = TextAreaField(
        "Additional Details",
        validators=[
            Optional(),
            Length(max=500, message="Details cannot exceed 500 characters"),
        ],
    )


# Payment Forms
class PaymentForm(FlaskForm):
    """Payment form"""

    booking_id = HiddenField("Booking ID", validators=[DataRequired()])
    amount = DecimalField(
        "Amount (KSh)",
        places=2,
        validators=[
            DataRequired(message="Amount is required"),
            NumberRange(min=100, message="Amount must be at least KSh 100"),
        ],
    )
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("mpesa", "M-Pesa"),
            ("card", "Credit/Debit Card"),
            ("bank_transfer", "Bank Transfer"),
        ],
        validators=[DataRequired(message="Payment method is required")],
    )

    # M-Pesa specific
    mpesa_phone = StringField(
        "M-Pesa Phone Number", validators=[Optional(), phone_validator]
    )

    # Card specific
    card_number = StringField(
        "Card Number",
        validators=[
            Optional(),
            Length(min=16, max=19, message="Enter a valid card number"),
            Regexp(r"^\d+$", message="Card number must contain only digits"),
        ],
    )
    card_expiry = StringField(
        "Expiry Date (MM/YY)",
        validators=[
            Optional(),
            Regexp(
                r"^(0[1-9]|1[0-2])\/([0-9]{2})$", message="Enter expiry date as MM/YY"
            ),
        ],
    )
    card_cvv = StringField(
        "CVV",
        validators=[
            Optional(),
            Length(min=3, max=4, message="CVV must be 3 or 4 digits"),
            Regexp(r"^\d+$", message="CVV must contain only digits"),
        ],
    )

    # Bank transfer specific
    bank_name = StringField("Bank Name", validators=[Optional()])
    account_number = StringField("Account Number", validators=[Optional()])


class WithdrawalRequestForm(FlaskForm):
    """Tutor withdrawal request form"""

    amount = DecimalField(
        "Withdrawal Amount (KSh)",
        places=2,
        validators=[
            DataRequired(message="Amount is required"),
            NumberRange(min=500, message="Minimum withdrawal is KSh 500"),
        ],
    )
    payment_method = SelectField(
        "Payment Method",
        choices=[("mpesa", "M-Pesa"), ("bank_transfer", "Bank Transfer")],
        validators=[DataRequired(message="Payment method is required")],
    )

    # M-Pesa
    mpesa_phone = StringField(
        "M-Pesa Phone Number",
        validators=[
            DataRequired(message="M-Pesa number is required")
            if "mpesa"
            else Optional(),
            phone_validator,
        ],
    )

    # Bank transfer
    bank_name = StringField(
        "Bank Name",
        validators=[
            DataRequired(message="Bank name is required")
            if "bank_transfer"
            else Optional()
        ],
    )
    account_name = StringField(
        "Account Name",
        validators=[
            DataRequired(message="Account name is required")
            if "bank_transfer"
            else Optional()
        ],
    )
    account_number = StringField(
        "Account Number",
        validators=[
            DataRequired(message="Account number is required")
            if "bank_transfer"
            else Optional(),
            Regexp(r"^\d+$", message="Account number must contain only digits"),
        ],
    )
    branch = StringField("Branch", validators=[Optional()])


# Review Forms
class ReviewForm(FlaskForm):
    """Review form"""

    rating = IntegerField(
        "Rating (1-5)",
        validators=[
            DataRequired(message="Rating is required"),
            NumberRange(min=1, max=5, message="Rating must be between 1 and 5"),
        ],
    )
    comment = TextAreaField(
        "Review Comment",
        validators=[
            DataRequired(message="Please write a review"),
            Length(
                min=10,
                max=1000,
                message="Review must be between 10 and 1000 characters",
            ),
        ],
    )
    would_recommend = BooleanField("Would recommend to others")


# Support Forms
class SupportTicketForm(FlaskForm):
    """Support ticket form"""

    subject = StringField(
        "Subject",
        validators=[
            DataRequired(message="Subject is required"),
            Length(
                min=5, max=200, message="Subject must be between 5 and 200 characters"
            ),
        ],
    )
    category = SelectField(
        "Category",
        choices=[
            ("technical", "Technical Issue"),
            ("billing", "Billing/Payment"),
            ("booking", "Booking Related"),
            ("account", "Account Issue"),
            ("safety", "Safety Concern"),
            ("feedback", "Feedback/Suggestion"),
            ("other", "Other"),
        ],
        validators=[DataRequired(message="Category is required")],
    )
    priority = SelectField(
        "Priority",
        choices=[
            ("low", "Low"),
            ("normal", "Normal"),
            ("high", "High"),
            ("urgent", "Urgent"),
        ],
        default="normal",
    )
    message = TextAreaField(
        "Message",
        validators=[
            DataRequired(message="Message is required"),
            Length(
                min=20,
                max=2000,
                message="Message must be between 20 and 2000 characters",
            ),
        ],
    )
    attachments = FileField(
        "Attachments (Optional)",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "pdf", "doc", "docx"],
                "Images, PDF or Word documents only!",
            ),
        ],
    )


class SupportReplyForm(FlaskForm):
    """Support reply form"""

    message = TextAreaField(
        "Reply",
        validators=[
            DataRequired(message="Reply is required"),
            Length(
                min=10, max=2000, message="Reply must be between 10 and 2000 characters"
            ),
        ],
    )
    attachments = FileField(
        "Attachments (Optional)",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "pdf", "doc", "docx"],
                "Images, PDF or Word documents only!",
            ),
        ],
    )


# Message Forms
class MessageForm(FlaskForm):
    """Message form"""

    recipient_id = HiddenField("Recipient ID", validators=[DataRequired()])
    booking_id = HiddenField("Booking ID", validators=[Optional()])
    message = TextAreaField(
        "Message",
        validators=[
            DataRequired(message="Message is required"),
            Length(min=1, max=2000, message="Message cannot exceed 2000 characters"),
        ],
    )
    attachments = FileField(
        "Attachments (Optional)",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "pdf", "doc", "docx", "txt"],
                "Images, documents or text files only!",
            ),
        ],
    )


# Search Forms
class TutorSearchForm(FlaskForm):
    """Tutor search form"""

    subject = SelectField(
        "Subject",
        choices=[
            ("", "Any Subject"),
            ("mathematics", "Mathematics"),
            ("english", "English"),
            ("kiswahili", "Kiswahili"),
            ("physics", "Physics"),
            ("chemistry", "Chemistry"),
            ("biology", "Biology"),
            ("history", "History"),
            ("geography", "Geography"),
            ("business", "Business Studies"),
            ("computer", "Computer Studies"),
            ("french", "French"),
            ("german", "German"),
            ("music", "Music"),
            ("art", "Art & Design"),
        ],
    )
    education_level = SelectField(
        "Education Level",
        choices=[
            ("", "Any Level"),
            ("primary", "Primary School"),
            ("form_1-2", "Form 1-2"),
            ("form_3-4", "Form 3-4"),
            ("college", "College/University"),
            ("adult", "Adult Learner"),
        ],
    )
    location = StringField("Location")
    min_rating = IntegerField(
        "Minimum Rating",
        validators=[
            Optional(),
            NumberRange(min=1, max=5, message="Rating must be between 1 and 5"),
        ],
        default=3,
    )
    max_rate = DecimalField(
        "Maximum Hourly Rate (KSh)",
        places=2,
        validators=[
            Optional(),
            NumberRange(min=100, message="Rate must be at least KSh 100"),
        ],
    )
    available_now = BooleanField("Available Now")
    verified_only = BooleanField("Verified Tutors Only", default=True)


# Admin Forms
class AdminUserForm(FlaskForm):
    """Admin user management form"""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required"),
            Length(
                min=3, max=50, message="Username must be between 3 and 50 characters"
            ),
            Regexp(
                r"^[a-zA-Z0-9_]+$",
                message="Username can only contain letters, numbers, and underscores",
            ),
        ],
    )
    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[DataRequired(message="Phone number is required"), phone_validator],
    )
    user_type = SelectField(
        "User Type",
        choices=[
            ("student", "Student"),
            ("tutor", "Tutor"),
            ("admin", "Admin"),
            ("super_admin", "Super Admin"),
        ],
        validators=[DataRequired(message="User type is required")],
    )
    is_active = BooleanField("Active", default=True)
    is_verified = BooleanField("Verified", default=False)
    is_super_admin = BooleanField("Super Admin")
    notes = TextAreaField(
        "Admin Notes",
        validators=[
            Optional(),
            Length(max=1000, message="Notes cannot exceed 1000 characters"),
        ],
    )


class AdminTutorForm(FlaskForm):
    """Admin tutor management form"""

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required"),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters"),
        ],
    )
    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
        ],
    )
    phone = StringField(
        "Phone Number",
        validators=[DataRequired(message="Phone number is required"), phone_validator],
    )
    id_number = StringField(
        "National ID Number",
        validators=[
            DataRequired(message="ID number is required"),
            Length(min=7, max=8, message="ID number must be 7 or 8 digits"),
            Regexp(r"^\d+$", message="ID number must contain only digits"),
        ],
    )
    subjects = SelectMultipleField(
        "Subjects", validators=[DataRequired(message="Select at least one subject")]
    )
    hourly_rate = DecimalField(
        "Hourly Rate (KSh)",
        places=2,
        validators=[
            DataRequired(message="Hourly rate is required"),
            NumberRange(
                min=100,
                max=10000,
                message="Hourly rate must be between KSh 100 and KSh 10,000",
            ),
        ],
    )
    rating = DecimalField(
        "Rating",
        places=1,
        validators=[
            Optional(),
            NumberRange(min=0, max=5, message="Rating must be between 0 and 5"),
        ],
    )
    is_verified = BooleanField("Verified", default=False)
    is_featured = BooleanField("Featured", default=False)
    is_available = BooleanField("Available", default=True)
    verification_notes = TextAreaField(
        "Verification Notes",
        validators=[
            Optional(),
            Length(max=1000, message="Notes cannot exceed 1000 characters"),
        ],
    )
    rejection_reason = TextAreaField(
        "Rejection Reason (if rejected)",
        validators=[
            Optional(),
            Length(max=1000, message="Reason cannot exceed 1000 characters"),
        ],
    )

class AnnouncementForm(FlaskForm):
    """Announcement form"""
    title = StringField('Title', validators=[
        DataRequired(message='Title is required'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    content = TextAreaField('Content', validators=[
        DataRequired(message='Content is required'),
        Length(min=20, max=5000, message='Content must be between 20 and 5000 characters')
    ])
    audience = SelectField('Audience', choices=[
        ('all', 'All Users'),
        ('students', 'Students Only'),
        ('tutors', 'Tutors Only'),
        ('admins', 'Admins Only')
    ], validators=[DataRequired(message='Audience is required')])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='normal')
    is_active = BooleanField('Active', default=True)
    publish_at = DateTimeField('Publish At', validators=[
        DataRequired(message='Publish date/time is required')
    ])
    expire_at = DateTimeField('Expire At', validators=[
        Optional()
    ])

class PlatformSettingForm(FlaskForm):
    """Platform setting form"""
    key = StringField('Key', validators=[
        DataRequired(message='Key is required'),
        Length(min=3, max=100, message='Key must be between 3 and 100 characters'),
        Regexp(r'^[a-zA-Z0-9_.]+$', message='Key can only contain letters, numbers, dots and underscores')
    ])
    value = StringField('Value', validators=[
        DataRequired(message='Value is required'),
        Length(max=1000, message='Value cannot exceed 1000 characters')
    ])
    category = SelectField('Category', choices=[
        ('general', 'General'),
        ('payment', 'Payment'),
        ('booking', 'Booking'),
        ('tutor', 'Tutor'),
        ('student', 'Student'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('security', 'Security'),
        ('maintenance', 'Maintenance')
    ], validators=[DataRequired(message='Category is required')])
    data_type = SelectField('Data Type', choices=[
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('array', 'Array')
    ], validators=[DataRequired(message='Data type is required')])
    description = TextAreaField('Description', validators=[
        DataRequired(message='Description is required'),
        Length(max=500, message='Description cannot exceed 500 characters')
    ])
    is_public = BooleanField('Public Setting', default=False)
    is_editable = BooleanField('Editable', default=True)

# OTP/2FA Forms
class OTPVerificationForm(FlaskForm):
    """OTP verification form"""
    otp = StringField('OTP Code', validators=[
        DataRequired(message='OTP is required'),
        Length(min=6, max=6, message='OTP must be 6 digits'),
        Regexp(r'^\d{6}$', message='OTP must contain only digits')
    ])

class Enable2FAForm(FlaskForm):
    """Enable 2FA form"""
    otp = StringField('OTP from Authenticator App', validators=[
        DataRequired(message='OTP is required'),
        Length(min=6, max=6, message='OTP must be 6 digits'),
        Regexp(r'^\d{6}$', message='OTP must contain only digits')
    ])
    backup_code = StringField('Backup Code (Save this!)', render_kw={'readonly': True})

# File Upload Forms
class DocumentUploadForm(FlaskForm):
    """Document upload form"""
    document_type = SelectField('Document Type', choices=[
        ('id', 'National ID'),
        ('certificate', 'Education Certificate'),
        ('resume', 'Resume/CV'),
        ('transcript', 'Academic Transcript'),
        ('reference', 'Reference Letter'),
        ('other', 'Other')
    ], validators=[DataRequired(message='Document type is required')])
    document = FileField('Document', validators=[
        FileRequired(message='Document is required'),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx'], 
                   'Images, PDF or Word documents only!')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500, message='Description cannot exceed 500 characters')
    ])

# Report Forms
class ReportForm(FlaskForm):
    """Report user form"""
    reported_user_id = HiddenField('Reported User ID', validators=[DataRequired()])
    reason = SelectField('Reason for Report', choices=[
        ('inappropriate_behavior', 'Inappropriate Behavior'),
        ('safety_concern', 'Safety Concern'),
        ('fake_profile', 'Fake Profile'),
        ('payment_issue', 'Payment Issue'),
        ('no_show', 'No Show/Cancellation'),
        ('harassment', 'Harassment'),
        ('other', 'Other')
    ], validators=[DataRequired(message='Reason is required')])
    details = TextAreaField('Details', validators=[
        DataRequired(message='Please provide details'),
        Length(min=20, max=1000, message='Details must be between 20 and 1000 characters')
    ])
    evidence = FileField('Evidence (Optional)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf', 'txt'], 
                   'Images, PDF or text files only!')
    ])

# Feedback Forms
class FeedbackForm(FlaskForm):
    """Platform feedback form"""
    feedback_type = SelectField('Feedback Type', choices=[
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('improvement', 'Improvement Suggestion'),
        ('general', 'General Feedback')
    ], validators=[DataRequired(message='Feedback type is required')])
    subject = StringField('Subject', validators=[
        DataRequired(message='Subject is required'),
        Length(min=5, max=200, message='Subject must be between 5 and 200 characters')
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message='Message is required'),
        Length(min=20, max=2000, message='Message must be between 20 and 2000 characters')
    ])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High')
    ], default='normal')
    contact_permission = BooleanField('I give permission to contact me about this feedback')

# Newsletter Forms
class NewsletterSubscriptionForm(FlaskForm):
    """Newsletter subscription form"""
    email = EmailField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    categories = SelectMultipleField('Categories of Interest', choices=[
        ('tutoring_tips', 'Tutoring Tips'),
        ('educational_resources', 'Educational Resources'),
        ('platform_updates', 'Platform Updates'),
        ('success_stories', 'Success Stories'),
        ('promotions', 'Promotions & Discounts')
    ])
    frequency = SelectField('Frequency', choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly')
    ], default='weekly')

# Export Forms
class DataExportForm(FlaskForm):
    """Data export form"""
    export_type = SelectField('Export Type', choices=[
        ('users', 'Users'),
        ('tutors', 'Tutors'),
        ('bookings', 'Bookings'),
        ('payments', 'Payments'),
        ('reviews', 'Reviews'),
        ('support_tickets', 'Support Tickets')
    ], validators=[DataRequired(message='Export type is required')])
    format = SelectField('Format', choices=[
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('excel', 'Excel')
    ], validators=[DataRequired(message='Format is required')])
    date_from = DateField('From Date', validators=[Optional()])
    date_to = DateField('To Date', validators=[Optional()])
    filters = TextAreaField('Additional Filters (JSON)', validators=[
        Optional(),
        Length(max=1000, message='Filters cannot exceed 1000 characters')
    ])

# Custom validators for specific forms
def validate_subjects_education_levels(self, field):
    """Validate that tutor teaches at least one education level for each subject"""
    if hasattr(self, 'subjects') and hasattr(self, 'education_levels'):
        if self.subjects.data and self.education_levels.data:
            # This is a simple validation - in practice, you might want more complex logic
            pass

TutorRegistrationForm.validate_subjects_education_levels = validate_subjects_education_levels
TutorProfileForm.validate_subjects_education_levels = validate_subjects_education_levels