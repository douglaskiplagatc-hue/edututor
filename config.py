# config.py
import os
from datetime import timedelta
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""

    # App settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    APP_NAME = os.environ.get("APP_NAME", "EduTutor Platform")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

    # Database
    import os

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace(
                "postgres://", "postgresql+psycopg2://", 1
            )
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"sslmode": "require"}  # required for Render
        }
    else:
        # fallback for local development
        SQLALCHEMY_DATABASE_URI = "sqlite:///tutor_kenya.db"

    # Security
    SECURITY_PASSWORD_SALT = os.environ.get(
        "SECURITY_PASSWORD_SALT", secrets.token_hex(16)
    )
    BCRYPT_LOG_ROUNDS = 12

    # Session
    SESSION_TYPE = "filesystem"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx"}

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

    # Admin settings
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@edututor.co.ke")
    SUPER_ADMIN_EMAILS = os.environ.get("SUPER_ADMIN_EMAILS", "").split(",")

    # Email settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "noreply@edututor.co.ke"
    )

    # SMS settings (Africa's Talking)
    AFRICAS_TALKING_USERNAME = os.environ.get("AFRICAS_TALKING_USERNAME")
    AFRICAS_TALKING_API_KEY = os.environ.get("AFRICAS_TALKING_API_KEY")
    AFRICAS_TALKING_SENDER_ID = os.environ.get("AFRICAS_TALKING_SENDER_ID", "EDUTUTOR")

    # Firebase Cloud Messaging (FCM)
    FCM_SERVER_KEY = os.environ.get("FCM_SERVER_KEY")
    FCM_SENDER_ID = os.environ.get("FCM_SENDER_ID")

    # Payment settings (M-Pesa)
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE")
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY")
    MPESA_CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL")
    MPESA_ENVIRONMENT = os.environ.get(
        "MPESA_ENVIRONMENT", "sandbox"
    )  # sandbox or production

    # Stripe settings
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

    # Platform settings
    PLATFORM_COMMISSION_PERCENTAGE = float(
        os.environ.get("PLATFORM_COMMISSION_PERCENTAGE", 20.0)
    )
    MINIMUM_WITHDRAWAL_AMOUNT = float(
        os.environ.get("MINIMUM_WITHDRAWAL_AMOUNT", 500.0)
    )
    MAX_BOOKING_HOURS = int(os.environ.get("MAX_BOOKING_HOURS", 4))
    MIN_BOOKING_NOTICE_HOURS = int(os.environ.get("MIN_BOOKING_NOTICE_HOURS", 2))

    # Cache settings
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "simple")
    CACHE_REDIS_URL = os.environ.get("REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", 300))

    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "app.log")

    # Testing
    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True

    # Database
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DEV_DATABASE_URL")
        or "postgresql://postgres:postgres@localhost/edututor_dev"
    )

    # Security (relaxed for development)
    SESSION_COOKIE_SECURE = False
    BCRYPT_LOG_ROUNDS = 4

    # Email
    MAIL_SUPPRESS_SEND = True  # Don't send emails in development
    MAIL_DEBUG = True

    # Payment
    MPESA_ENVIRONMENT = "sandbox"

    # Logging
    LOG_LEVEL = "DEBUG"

    # CORS
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
    ]

    # Enable detailed error pages
    PROPAGATE_EXCEPTIONS = True

    # Disable caching for development
    CACHE_TYPE = "null"


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    DEBUG = True

    # Use in-memory SQLite database for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    # Security
    SECRET_KEY = "testing-secret-key"
    SECURITY_PASSWORD_SALT = "testing-salt"
    BCRYPT_LOG_ROUNDS = 4

    # Disable CSRF protection for testing
    WTF_CSRF_ENABLED = False

    # Email
    MAIL_SUPPRESS_SEND = True

    # Payment
    MPESA_ENVIRONMENT = "sandbox"

    # Disable rate limiting for testing
    RATELIMIT_ENABLED = False

    # Disable caching
    CACHE_TYPE = "null"

    # Test data
    TEST_ADMIN_EMAIL = "testadmin@edututor.co.ke"
    TEST_ADMIN_PASSWORD = "testadmin123"
    TEST_TUTOR_EMAIL = "testtutor@edututor.co.ke"
    TEST_STUDENT_EMAIL = "teststudent@edututor.co.ke"


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "max_overflow": 20,
        "connect_args": {"connect_timeout": 10, "application_name": "edututor_app"},
    }

    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"

    # Email
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    # Payment
    MPESA_ENVIRONMENT = "production"

    # Cache
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.environ.get("REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = 600

    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "1000 per day;100 per hour"

    # Logging
    LOG_LEVEL = "WARNING"
    LOG_FILE = "/var/log/edututor/app.log"

    # Upload folder
    UPLOAD_FOLDER = "/var/www/edututor/uploads"

    # Performance
    JSONIFY_PRETTYPRINT_REGULAR = False

    # Security headers middleware settings
    SECURITY_HEADERS = {
        "Content-Security-Policy": "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    # Monitoring
    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    # Backup settings
    BACKUP_DIR = "/var/backups/edututor"
    BACKUP_RETENTION_DAYS = 30


class StagingConfig(ProductionConfig):
    """Staging configuration"""

    DEBUG = True

    # Use different database for staging
    SQLALCHEMY_DATABASE_URI = os.environ.get("STAGING_DATABASE_URL")

    # Payment
    MPESA_ENVIRONMENT = "sandbox"

    # Email - send to staging addresses only
    MAIL_SUPPRESS_SEND = False
    MAIL_OVERRIDE_RECIPIENT = os.environ.get("STAGING_MAIL_RECIPIENT")

    # Logging
    LOG_LEVEL = "INFO"

    # Security (slightly relaxed for testing)
    SESSION_COOKIE_SAMESITE = "Lax"


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "staging": StagingConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name=None):
    """
    Get configuration class based on environment variable.

    Args:
        config_name: Configuration name (development, testing, production, staging)

    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_class = config.get(config_name.lower())

    if config_class is None:
        raise ValueError(f"Invalid configuration name: {config_name}")

    return config_class


# Helper function to get current config
def get_current_config():
    """Get the current active configuration"""
    from flask import current_app

    return current_app.config
