from app import create_app, db
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app instance
app = create_app()

with app.app_context():
    try:
        # Create all database tables
        db.create_all()
        logger.info("Database tables created")

    except Exception as e:
        logger.error(f"Error initializing the database: {e}")
        raise
