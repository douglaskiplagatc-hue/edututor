# check_render.py
import os
import sys

def check_render_readiness():
    """Check if app is ready for Render deployment"""
    
    checks = []
    
    # 1. Check required files
    required_files = ['requirements.txt', 'wsgi.py', 'Procfile']
    for file in required_files:
        if os.path.exists(file):
            checks.append((f"✓ {file} exists", True))
        else:
            checks.append((f"✗ Missing: {file}", False))
    
    # 2. Check requirements
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            content = f.read()
            if 'gunicorn' in content or 'psycopg2' in content:
                checks.append(("✓ requirements.txt has production packages", True))
            else:
                checks.append(("⚠ Add gunicorn and psycopg2-binary to requirements", False))
    
    # 3. Check environment variables
    required_env_vars = ['SECRET_KEY', 'DATABASE_URL']
    for var in required_env_vars:
        if var in os.environ:
            checks.append((f"✓ {var} is set", True))
        else:
            checks.append((f"⚠ {var} should be set in production", var != 'DATABASE_URL'))
    
    # 4. Check database configuration
    try:
        from config import ProductionConfig
        config = ProductionConfig()
        if 'render.com' in getattr(config, 'SQLALCHEMY_DATABASE_URI', ''):
            checks.append(("✓ Database configured for Render", True))
        else:
            checks.append(("⚠ Check database configuration", False))
    except:
        checks.append(("⚠ Could not load config", False))
    
    # Print results
    print("=== Render Deployment Checklist ===")
    all_pass = True
    for check, passed in checks:
        print(check)
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✅ Ready for Render deployment!")
        return 0
    else:
        print("\n❌ Fix issues before deploying to Render")
        return 1

if __name__ == '__main__':
    sys.exit(check_render_readiness())