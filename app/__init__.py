from flask import Flask
import sqlite3
import os
from app.routes import routes

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder='app/templates')
    
    # Debug: Print template folder path
    print("Template folder:", os.path.abspath(app.template_folder))
    
    # Configuration
    UPLOAD_FOLDER = 'Uploads'
    LOG_DB = 'logs/analyzer.db'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # Ensure directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    def init_db():
        """Initialize SQLite database for analysis logs."""
        conn = sqlite3.connect(LOG_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at DATETIME,
                original_code TEXT,
                analysis_results TEXT,
                optimized_code TEXT,
                conversation_history TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    # Initialize database
    init_db()
    
    # Register blueprints
    app.register_blueprint(routes)
    
    return app