import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'this-is-a-very-secret-key'
    
    # Build the SQL Server connection string from environment variables
    # SQLALCHEMY_DATABASE_URI = (
    #     f"mssql+pyodbc://"
    #     f"{os.environ.get('AZURE_SQL_USERNAME')}:"
    #     f"{os.environ.get('AZURE_SQL_PASSWORD')}@"
    #     f"{os.environ.get('AZURE_SQL_SERVER')}/"
    #     f"{os.environ.get('AZURE_SQL_DATABASE')}"
    #     "?driver=ODBC+Driver+18+for+SQL+Server"
    #     "&Encrypt=yes"
    #     "&TrustServerCertificate=no"
    # )

    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT', '3307')}/{os.environ.get('DB_NAME')}"
    
    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    
    # Additional configuration for production
    if os.environ.get('FLASK_ENV') == 'production':
        SESSION_COOKIE_SECURE = True
        SESSION_COOKIE_HTTPONLY = True
        REMEMBER_COOKIE_SECURE = True
        REMEMBER_COOKIE_HTTPONLY = True
