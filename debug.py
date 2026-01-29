import os
import sys
from flask import render_template
from app.__init__ import create_app

print("🔍 DEBUGGING FLASK APP")
print("=" * 50)

# Check project structure
print("\n1. PROJECT STRUCTURE:")
for root, dirs, files in os.walk("."):
    level = root.replace(".", "").count(os.sep)
    indent = " " * 4 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 4 * (level + 1)
    for file in files[:10]:  # Show first 10 files
        if file.endswith((".py", ".html", ".txt", ".json")):
            print(f"{subindent}{file}")

# Check templates
print("\n2. TEMPLATES DIRECTORY:")
templates_path = os.path.join("app", "templates")
if os.path.exists(templates_path):
    print(f"✅ Found templates at: {templates_path}")
    templates = os.listdir(templates_path)
    print(f"   Templates found: {len(templates)}")
    for template in templates:
        print(f"   - {template}")
else:
    print(f"❌ Missing templates directory at: {templates_path}")

# Check Flask config
print("\n3. FLASK CONFIGURATION:")
try:
    from app import create_app

    app = create_app()
    print(f"✅ Flask app created successfully")
    print(f"   Template folder: {app.template_folder}")
    print(f"   Static folder: {app.static_folder}")
    print(f"   Debug mode: {app.debug}")
except Exception as e:
    print(f"❌ Error creating app: {e}")
app = create_app()
with app.app_context():
    render_template("index.html")
# Test template rendering
print("\n4. TEMPLATE RENDERING TEST:")
try:
    from flask import render_template_string

    test_html = "<h1>Test {{ message }}</h1>"
    result = render_template_string(test_html, message="Success!")
    print(f"✅ Template engine working: {result[:50]}...")
except Exception as e:
    print(f"❌ Template engine error: {e}")

print("\n" + "=" * 50)
print("Run: python debug.py to see current status")
