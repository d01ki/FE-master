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
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')  # デフォルトを development に変更
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'  # デフォルトを True に変更

    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # Detect database type from URL
        if DATABASE_URL.startswith('mysql://'):
            DATABASE_TYPE = 'mysql'
        elif DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://'):
            # Normalize postgres scheme (for backwards compatibility)
            if DATABASE_URL.startswith("postgres://"):
                DATABASE_URL = DATABASE_URL.replace("postgres://", "mysql://", 1)
            DATABASE_TYPE = 'mysql'  # RDS uses MySQL now
        else:
            DATABASE_TYPE = 'sqlite'
    else:
        DATABASE_TYPE = 'sqlite'
        DATABASE_URL = 'sqlite:///fe_exam.db'

    # Parse MySQL URL if needed
    if DATABASE_TYPE == 'mysql':
        # mysql://username:password@host:port/database
        match = re.match(r'mysql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', DATABASE_URL)
        if match:
            DB_USER = match.group(1)
            DB_PASSWORD = match.group(2)
            DB_HOST = match.group(3)
            DB_PORT = int(match.group(4)) if match.group(4) else 3306
            DB_NAME = match.group(5)
        else:
            raise ValueError('Invalid MySQL DATABASE_URL format')
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
        if cls.DATABASE_TYPE == 'mysql':
            return {
                'DATABASE_TYPE': 'mysql',
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

