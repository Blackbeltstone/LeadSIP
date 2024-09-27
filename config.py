import os

# Get the base directory of the current file
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for session management and other security-related operations
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')

    # Database URI: Use the DATABASE_URL from environment, or fallback to SQLite for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'instance/site.db'))
    
    # Disable tracking modifications to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Folder for uploaded files (e.g., images, documents)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(basedir, 'app', 'static', 'uploads'))
    
    # Folder for storing generated QR codes
    QR_FOLDER = os.environ.get('QR_FOLDER', os.path.join(basedir, 'app', 'static', 'qr_codes'))
    
    # Allowed file extensions for uploads, defaulting to common image formats
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif').split(','))

class ProductionConfig(Config):
    # Disable debug mode in production
    DEBUG = False

class DevelopmentConfig(Config):
    # Enable debug mode for development
    DEBUG = True
