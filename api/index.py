import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from config import Config

app = create_app(Config)

if __name__ == "__main__":
    app.run()