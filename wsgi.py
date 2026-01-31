"""
WSGI entry point for production deployment
"""
import os
from app import create_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create application instance
app = create_app(os.environ.get('FLASK_CONFIG', 'production'))

# Health check endpoint
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'edututor'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
