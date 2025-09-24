"""
Configuration file for the application
Loads settings from environment variables
"""
import os
from dotenv import load_dotenv
import re

# Load environment variables (for local development)
load_dotenv()

class Config:
    """Application configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # Normalize postgres scheme (Render often gives postgres://)
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        if DATABASE_URL.startswith('postgresql://'):
            DATABASE_TYPE = 'postgresql'
        else:
            DATABASE_TYPE = 'sqlite'
    else:
        DATABASE_TYPE = 'sqlite'
        DATABASE_URL = 'sqlite:///fe_exam.db'

    # Parse PostgreSQL URL if needed
    if DATABASE_TYPE == 'postgresql':
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):?(\d+)?/(.+)', DATABASE_URL)
        if match:
            DB_USER = match.group(1)
            DB_PASSWORD = match.group(2)
            DB_HOST = match.group(3)
            DB_PORT = match.group(4) or '5432'
            DB_NAME = match.group(5)
        else:
            raise ValueError('Invalid PostgreSQL DATABASE_URL format')
    else:
        DB_USER = None
        DB_PASSWORD = None
        DB_HOST = None
        DB_PORT = None
        DB_NAME = DATABASE_URL.replace('sqlite:///', '')

    # Admin settings (optional, for initial setup)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

    # Server settings
    PORT = int(os.environ.get('PORT', 5002))
    HOST = os.environ.get('HOST', '0.0.0.0')

    @classmethod
    def get_db_config(cls):
        """Get database configuration dictionary"""
        if cls.DATABASE_TYPE == 'postgresql':
            return {
                'DATABASE_TYPE': 'postgresql',
                'DB_NAME': cls.DB_NAME,
                'DB_USER': cls.DB_USER,
                'DB_PASSWORD': cls.DB_PASSWORD,
                'DB_HOST': cls.DB_HOST,
                'DB_PORT': cls.DB_PORT
            }
        else:
            return {
                'DATABASE_TYPE': 'sqlite',
                'DATABASE': cls.DB_NAME
            }
