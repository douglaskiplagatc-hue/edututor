import os
from datetime import timedelta

class ProductionConfig:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_MAX_OVERFLOW = 100
    SQLALCHEMY_POOL_RECYCLE = 3600
    
    # Security
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # M-Pesa
    MPESA_ENV = os.environ.get('MPESA_ENV', 'production')
    MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY')
    MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET')
    MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE')
    MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY')
    MPESA_CALLBACK_URL = os.environ.get('MPESA_CALLBACK_URL')
    
    # Video Calls
    ZOOM_API_KEY = os.environ.get('ZOOM_API_KEY')
    ZOOM_API_SECRET = os.environ.get('ZOOM_API_SECRET')
    ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID')
    DAILY_CO_API_KEY = os.environ.get('DAILY_CO_API_KEY')
    
    # Push Notifications
    FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY')
    AT_API_KEY = os.environ.get('AT_API_KEY')
    AT_USERNAME = os.environ.get('AT_USERNAME')
    
    # Redis & Celery
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    # Cache
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # API
    API_VERSION = '1.0'
    API_TITLE = 'EduTutor Kenya API'
    API_DESCRIPTION = 'API for EduTutor Kenya Platform'
    
    # Performance
    JSONIFY_PRETTYPRINT_REGULAR = False
    TEMPLATES_AUTO_RELOAD = False
    EXPLAIN_TEMPLATE_LOADING = False
    
    # Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # CDN
    CDN_DOMAIN = os.environ.get('CDN_DOMAIN')
    
    @staticmethod
    def init_app(app):
        # Initialize monitoring
        if ProductionConfig.SENTRY_DSN:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            sentry_sdk.init(
                dsn=ProductionConfig.SENTRY_DSN,
                integrations=[FlaskIntegration()],
                traces_sample_rate=1.0
            )
        
        # Setup logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/edututor.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('EduTutor Kenya startup')