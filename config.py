import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hairsync_default_secret_key_mca')
    
    # Database configuration (SQLite)
    DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'instance', 'hairsync.db'))
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'donors')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB maximum file upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
