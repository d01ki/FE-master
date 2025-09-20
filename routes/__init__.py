"""
ルーティングモジュール
"""
from .main_routes import main_bp
from .practice_routes import practice_bp
from .exam_routes import exam_bp
from .admin_routes import admin_bp
from .ranking_routes import ranking_bp

__all__ = ['main_bp', 'practice_bp', 'exam_bp', 'admin_bp', 'ranking_bp']
