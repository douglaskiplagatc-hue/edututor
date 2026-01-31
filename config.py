# config.py - UPDATED FOR RENDER
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
    
    # Database configuration for Render
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Get DATABASE_URL from Render environment
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if DATABASE_URL:
        # Render provides postgres:// URL, need to convert to postgresql://
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Local development fallback
        SQLALCHEMY_DATABASE_URI = "sqlite:///tutor_kenya.db"
    
    # Security
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", secrets.token_hex(16))
    BCRYPT_LOG_ROUNDS = 12
    
    # Session
    SESSION_TYPE = "filesystem"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # File upload (adjust for Render)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx"}
    
    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
    
    # Email settings (configure in Render)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@edututor.co.ke")
    
    # Payment settings
    MPESA_ENVIRONMENT = os.environ.get("MPESA_ENVIRONMENT", "sandbox")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    
    # Platform settings
    PLATFORM_COMMISSION_PERCENTAGE = float(os.environ.get("PLATFORM_COMMISSION_PERCENTAGE", 20.0))
    MINIMUM_WITHDRAWAL_AMOUNT = float(os.environ.get("MINIMUM_WITHDRAWAL_AMOUNT", 500.0))
    
    # Cache settings
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "simple")
    CACHE_REDIS_URL = os.environ.get("REDIS_URL")
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")


class DevelopmentConfig(Config):
    """Development configuration"""
    
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///edututor_dev.db"  # Simple SQLite for development
    SESSION_COOKIE_SECURE = False
    MAIL_SUPPRESS_SEND = True
    CACHE_TYPE = "simple"


class ProductionConfig(Config):
    """Production configuration for Render"""
    
    DEBUG = False
    
    # Render PostgreSQL (already handled in base Config)
    
    # Production optimizations
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    
    # Production cache (use Render Redis if available)
    if os.environ.get("REDIS_URL"):
        CACHE_TYPE = "redis"
        CACHE_REDIS_URL = os.environ.get("REDIS_URL")
    
    # Logging
    LOG_LEVEL = "WARNING"


class TestingConfig(Config):
    """Testing configuration"""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    RATELIMIT_ENABLED = False


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}