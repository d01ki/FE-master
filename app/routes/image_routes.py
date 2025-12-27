"""
画像配信ルート - 認証が必要な保護された画像の配信
"""
import os
from flask import Blueprint, send_from_directory, abort, current_app
from app.core.auth import login_required

image_bp = Blueprint('images', __name__)

@image_bp.route('/images/questions/<filename>')
@login_required
def serve_question_image(filename):
    """
    問題画像の配信（認証必須）
    
    Args:
        filename: 画像ファイル名
        
    Returns:
        画像ファイル
    """
    # セキュリティ: ファイル名のサニタイズ
    if '..' in filename or '/' in filename:
        abort(403)
    
    # 許可された拡張子のチェック
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        abort(403)
    
    # 画像ディレクトリのパス
    images_dir = os.path.join(current_app.config['PROTECTED_IMAGES_DIR'], 'questions')
    
    # ファイルの存在確認
    filepath = os.path.join(images_dir, filename)
    if not os.path.exists(filepath):
        abort(404)
    
    return send_from_directory(images_dir, filename)


@image_bp.route('/images/answers/<filename>')
@login_required
def serve_answer_image(filename):
    """
    解答画像の配信（認証必須）
    
    Args:
        filename: 画像ファイル名
        
    Returns:
        画像ファイル
    """
    # セキュリティ: ファイル名のサニタイズ
    if '..' in filename or '/' in filename:
        abort(403)
    
    # 許可された拡張子のチェック
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        abort(403)
    
    # 画像ディレクトリのパス
    images_dir = os.path.join(current_app.config['PROTECTED_IMAGES_DIR'], 'answers')
    
    # ファイルの存在確認
    filepath = os.path.join(images_dir, filename)
    if not os.path.exists(filepath):
        abort(404)
    
    return send_from_directory(images_dir, filename)
