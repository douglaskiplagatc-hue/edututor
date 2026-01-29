import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

print("🔍 Testing imports...")
print("=" * 50)

# Test 1: Import blueprints
try:
    from app.routes import main, auth, tutor, api
    print("✅ Blueprints imported successfully!")
    print(f"   main: {type(main).__name__}")
    print(f"   auth: {type(auth).__name__}")
    print(f"   tutor: {type(tutor).__name__}")
    print(f"   api: {type(api).__name__}")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTrying to see what's available...")
    
    # Check routes.py directly
    import ast
    with open("app/routes.py", "r") as f:
        content = f.read()
    
    # Look for Blueprint definitions
    import re
    blueprints = re.findall(r'(\w+)\s*=\s*Blueprint', content)
    print(f"\nFound blueprint definitions: {blueprints}")
    
    if 'tutor_bp' in blueprints and 'tutor' not in blueprints:
        print("\n⚠️ ISSUE: You have 'tutor_bp' but trying to import 'tutor'")
        print("   Fix: Change 'tutor_bp' to 'tutor' in routes.py")
        print("   OR: Change import to 'tutor_bp as tutor'")

# Test 2: Create Flask app
print("\n" + "=" * 50)
print("Testing Flask app creation...")
try:
    from app import create_app
    app = create_app()
    print("✅ Flask app created successfully!")
    
    # Test routes
    print("\nAvailable routes:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            print(f"   {rule.rule} → {rule.endpoint}")
except Exception as e:
    print(f"❌ Error creating app: {e}")

print("\n" + "=" * 50)
