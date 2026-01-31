# setup.py
import os
import sys
from app import create_app, db

def setup_database():
    """Setup database with proper configuration"""
    
    print("=== Setting up EduTutor Database ===")
    
    # Set Termux environment
    os.environ['ANDROID_ROOT'] = '/system'
    os.environ['FLASK_ENV'] = 'development'
    
    # Create app with development config
    app = create_app('development')
    
    with app.app_context():
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Created {len(tables)} tables: {tables}")
        
        return True

if __name__ == '__main__':
    try:
        if setup_database():
            print("\n✅ Setup completed successfully!")
            print("\nTo run the app:")
            print("1. export FLASK_APP=app.py")
            print("2. export FLASK_ENV=development")
            print("3. flask run --host=0.0.0.0 --port=5000")
        else:
            print("\n❌ Setup failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)