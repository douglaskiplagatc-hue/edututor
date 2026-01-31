#!/bin/bash
# deploy.sh - Deployment script for Render

echo "=== EduTutor Deployment to Render ==="

# Check if all required files exist
echo "Checking required files..."
required_files=("requirements.txt" "wsgi.py" "Procfile" "runtime.txt")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ Missing: $file"
        exit 1
    fi
done

# Create .env.production template if not exists
if [ ! -f ".env.production" ]; then
    echo "Creating .env.production template..."
    cat > .env.production << 'EOF'
# Production Environment Variables for Render
SECRET_KEY=your-production-secret-key-here
SECURITY_PASSWORD_SALT=your-production-salt-here

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Payment Configuration
MPESA_ENVIRONMENT=sandbox
STRIPE_SECRET_KEY=your-stripe-secret-key

# Platform Settings
PLATFORM_COMMISSION_PERCENTAGE=20.0
MINIMUM_WITHDRAWAL_AMOUNT=500.0

# Redis (if using)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
EOF
    echo "Created .env.production template. Update with your values!"
fi

# Create .gitignore if not exists
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
venv/
env/
ENV/

# Environment
.env
.env.local
.env.production
.env.development

# Database
*.db
*.sqlite3

# Uploads
uploads/
static/uploads/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/
EOF
fi

echo ""
echo "=== Ready for Git ==="
echo "Run these commands to deploy:"
echo ""
echo "1. Initialize Git repository:"
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial commit: EduTutor platform'"
echo ""
echo "2. Push to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Deploy to Render:"
echo "   - Go to https://dashboard.render.com"
echo "   - Click 'New +' → 'Web Service'"
echo "   - Connect your GitHub repository"
echo "   - Use these settings:"
echo "     • Name: edututor-platform"
echo "     • Environment: Python"
echo "     • Build Command: pip install -r requirements.txt"
echo "     • Start Command: gunicorn wsgi:app --bind 0.0.0.0:\$PORT"
echo "   - Add environment variables from .env.production"
echo "   - Click 'Create Web Service'"
echo ""
echo "=== Deployment Complete ==="