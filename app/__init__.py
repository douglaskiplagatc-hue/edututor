# app/__init__.py - Fixed version
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from celery import Celery
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
cors = CORS()
socketio = SocketIO()
limiter = Limiter(
    key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)
cache = Cache()
celery = Celery(
    __name__, broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)


def create_app(config_name="development"):
    """Create Flask application"""

    app = Flask(__name__)

    # Import config
    from config import DevelopmentConfig, ProductionConfig, TestingConfig

    # Load configuration based on name
    if config_name == "production":
        app.config.from_object(ProductionConfig)
    elif config_name == "testing":
        app.config.from_object(TestingConfig)
    else:  # development
        app.config.from_object(DevelopmentConfig)

    # Print debug info for Termux
    if "ANDROID_ROOT" in os.environ:
        print(
            f"[Termux] Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')}"
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")
    limiter.init_app(app)
    cache.init_app(app)

    # Setup login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Create upload directories
    create_upload_dirs(app)

    # Setup celery
    celery.conf.update(app.config)

    return app


def get_config_class(config_name):
    """Get config class from string"""
    from config import ProductionConfig, DevelopmentConfig, TestingConfig

    config_map = {
        "production": ProductionConfig,
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "default": DevelopmentConfig,
    }
    return config_map.get(config_name, DevelopmentConfig)


def register_blueprints(app):
    """Register all blueprints"""
    from app.routes import main, auth, hometutor, api
    from app.admin_routes import admin
    from mobile_api.auth import mobile_auth
    from mobile_api.bookings import mobile_bookings
    from mobile_api.tutors import mobile_tutors

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(hometutor)
    app.register_blueprint(api, url_prefix="/api/v1")
    app.register_blueprint(admin, url_prefix="/admin")
    app.register_blueprint(mobile_auth, url_prefix="/api/mobile/v1/auth")
    app.register_blueprint(mobile_bookings, url_prefix="/api/mobile/v1/bookings")
    app.register_blueprint(mobile_tutors, url_prefix="/api/mobile/v1/tutors")


def register_error_handlers(app):
    """Register error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify(
            {
                "error": "ratelimit exceeded",
                "message": "Too many requests. Please try again later.",
            }
        ), 429


def create_upload_dirs(app):
    """Create necessary upload directories"""
    upload_dirs = [
        "static/uploads/profile_pics",
        "static/uploads/certificates",
        "static/uploads/lesson_materials",
        "static/uploads/temp",
    ]

    for directory in upload_dirs:
        os.makedirs(os.path.join(app.root_path, directory), exist_ok=True)


# Import models after db initialization to avoid circular imports
from app import models
