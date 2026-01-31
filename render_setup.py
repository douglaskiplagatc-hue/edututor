# render_setup.py
import os
import sys

# Set production environment
os.environ['FLASK_ENV'] = 'production'

try:
    from app import create_app, db
    print("=== Initializing EduTutor Database for Render ===")
    
    app = create_app('production')
    
    with app.app_context():
        # Create tables
        db.create_all()
        print("✓ Database tables created")
        
        # Show tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        print("\n✅ Database initialized successfully!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)