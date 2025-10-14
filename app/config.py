import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'this-is-a-very-secret-key'
    
    # Build the SQL Server connection string from environment variables
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pyodbc://"
        f"{os.environ.get('AZURE_SQL_USERNAME')}:"
        f"{os.environ.get('AZURE_SQL_PASSWORD')}@"
        f"{os.environ.get('AZURE_SQL_SERVER')}/"
        f"{os.environ.get('AZURE_SQL_DATABASE')}"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&Encrypt=yes"
        "&TrustServerCertificate=no"
    )

    # SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT', '3307')}/{os.environ.get('DB_NAME')}"
    
    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQL Server specific settings to avoid OUTPUT clause conflicts with triggers
    SQLALCHEMY_ENGINE_OPTIONS = {
        'implicit_returning': False,  # Disable OUTPUT clause for SQL Server triggers
        'pool_pre_ping': True,        # Connection health check
        'pool_recycle': 300           # Recycle connections every 5 minutes
    }
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    SESSION_PERMANENT = True
    
    # Remember me configuration - sessions last 30 days
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    
    # Cookie security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = bool(os.environ.get('FLASK_COOKIE_SECURE', False))
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = bool(os.environ.get('FLASK_COOKIE_SECURE', False))
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    # Additional configuration for production
    if os.environ.get('FLASK_ENV') == 'production':
        SESSION_COOKIE_SECURE = True
        REMEMBER_COOKIE_SECURE = True
