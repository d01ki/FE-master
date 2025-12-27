"""
模擬試験関連のルーティング
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, current_app
from app.core.auth import login_required
import os
import json
import random
import re
import uuid

exam_bp = Blueprint('exam', __name__)

# メモリ内に試験データを保存（本番ではRedisなど使用）
exam_sessions = {}

def is_image_url(text):
    """テキストが画像URLかどうかを判定"""
    if not text or not isinstance(text, str):
        return False
    
    image_patterns = [
        r'/static/images/',
        r'\.png$',
        r'\.jpg$',
        r'\.jpeg$',
        r'\.gif$',
        r'\.svg$',
        r'\.webp$'
    ]
    
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in image_patterns)

def add_image_choice_flags(questions):
    """問題リストに has_image_choices フラグを追加"""
    for question in questions:
        question['has_image_choices'] = False
        if question.get('choices'):
            # 最初の選択肢をチェック
            first_choice = list(question['choices'].values())[0]
            question['has_image_choices'] = is_image_url(first_choice)
    return questions


def normalize_media_value(val):
    """Normalize image path/URL; return None when empty."""
    if not val or not isinstance(val, str):
        return None
    cleaned = val.strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace('\\', '/')

    # Absolute or repo-contained protected images
    if 'protected_images/questions/' in cleaned:
        fname = cleaned.split('/')[-1]
        return f'/images/questions/{fname}'

    # Existing protected route or static
    if cleaned.startswith('/images/questions/'):
        return cleaned
    if cleaned.startswith('images/questions/'):
        return '/' + cleaned
    if cleaned.startswith('/static/'):
        return cleaned
    if cleaned.startswith('static/'):
        return '/' + cleaned

    # If it looks like just a filename, map to protected route
    if '/' not in cleaned:
        return f'/images/questions/{cleaned}'

    # Default fallthrough
    return cleaned


def sanitize_question_text(text):
    """Remove stray image path fragments from question text."""
    if not text or not isinstance(text, str):
        return text
    patterns = [
        r'/image\\?s?/question[s]?/[^\s]+',
        r'images?/questions?/[^\s]+' ,
        r'protected_images/questions/[^\s]+'
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def normalize_choice_value(val):
    """Normalize choice text or image path, dropping noisy JSON blobs."""
    if val is None:
        return None
    if not isinstance(val, str):
        val = str(val)
    s = val.strip()
    if not s:
        return None

    lower = s.lower()
    # Keep image-like values as media paths
    if re.search(r'(\.png|\.jpg|\.jpeg|\.gif|\.svg|\.webp)$', lower) or '/image' in lower or 'protected_images/questions/' in lower:
        return normalize_media_value(s) or s

    # If the value itself is JSON, try to decode; drop non-string payloads
    if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
        try:
            decoded = json.loads(s)
            if isinstance(decoded, str):
                s = decoded.strip()
            else:
                return None
        except Exception:
            return None

    s = sanitize_question_text(s)
    return s if s else None

def parse_filename_info(filename_or_id):
    """Parse year/season from filename or question_id (e.g., 2024r06_kamoku_a_spring.json)."""
    target = filename_or_id or ''
    basename = os.path.splitext(str(target).lower())[0]
    tokens = basename.split('_')

    # 年度は最初に出現する4桁数字
    year = None
    for token in tokens:
        match = re.match(r'(\d{4})', token)
        if match:
            year = match.group(1)
            break

    if not year:
        return None

    # 期は末尾側のトークンから探索
    season_raw = None
    for token in reversed(tokens):
        if token in ('spring', 's', 'fall', 'f', 'autumn'):
            season_raw = token
            break

    if not season_raw:
        return None

    canonical_season = {
        'spring': 'spring',
        's': 'spring',
        'fall': 'fall',
        'f': 'fall',
        'autumn': 'fall'
    }.get(season_raw, season_raw)

    season_map = {
        'spring': '春期',
        'fall': '秋期'
    }

    season_order_map = {
        '春期': 2,  # 降順ソート時に春期を先に出す
        '秋期': 1
    }

    season = season_map.get(canonical_season, canonical_season)
    season_order = season_order_map.get(season, 0)

    return {
        'filename': filename_or_id,
        'year': year,
        'season': season,
        'season_code': canonical_season,
        'display_name': f'{year}年度 {season}',
        'sort_key': (int(year), season_order),
        'exam_code': f"{year}_{canonical_season}"
    }

@exam_bp.route('/mock_exam')
@login_required
def mock_exam():
    """模擬試験のトップページ"""
    # DBに登録済みの問題IDから年度・期を推定して一覧化
    question_ids = current_app.db_manager.execute_query(
        'SELECT question_id FROM questions WHERE question_id IS NOT NULL'
    ) or []

    exam_index = {}
    files = []

    for row in question_ids:
        qid = row.get('question_id') if isinstance(row, dict) else None
        info = parse_filename_info(qid)
        if not info:
            continue

        exam_code = info['exam_code']
        if exam_code not in exam_index:
            exam_index[exam_code] = {
                'exam_code': exam_code,
                'year': info['year'],
                'season': info['season'],
                'display_name': info['display_name'],
                'sort_key': info['sort_key'],
                'count': 0,
            }
            files.append(exam_index[exam_code])

        exam_index[exam_code]['count'] += 1

    print(f"Total mock exam sets found: {len(files)}")

    if not files:
        return render_template('mock_exam.html', files=[], grouped_years=[], grouped_files={})

    files.sort(key=lambda x: x['sort_key'], reverse=True)

    # 年度単位でグルーピング
    grouped = {}
    for f in files:
        year = f['year']
        grouped.setdefault(year, []).append(f)

    # 各年の期をソート（春→秋の順で表示するためsort_key降順）
    for year in grouped:
        grouped[year] = sorted(grouped[year], key=lambda x: x['sort_key'], reverse=True)

    # 表示用に年を降順
    ordered_years = sorted(grouped.keys(), reverse=True)

    return render_template('mock_exam.html', files=files, grouped_years=ordered_years, grouped_files=grouped)

@exam_bp.route('/mock_exam/<exam_code>')
@login_required
def mock_exam_start(exam_code):
    """指定年度の模擬試験開始（DB上の問題を使用）"""
    try:
        normalized_code = str(exam_code).lower()
        parts = normalized_code.split('_', 1)
        if len(parts) != 2:
            flash('無効な試験指定です', 'error')
            return redirect(url_for('exam.mock_exam'))

        year, season_code = parts[0], parts[1]

        season_display = {
            'spring': '春期',
            'fall': '秋期',
        }.get(season_code, season_code)

        # DBから該当試験の問題を抽出（安定した順序で取得）
        all_questions = current_app.db_manager.execute_query('SELECT * FROM questions ORDER BY id') or []
        matched_questions = []

        for row in all_questions:
            qid = row.get('question_id') if isinstance(row, dict) else None
            meta = parse_filename_info(qid)
            if not meta:
                continue
            if meta['exam_code'] != normalized_code:
                continue

            q = dict(row)

            # question text sanitize (remove stray image path fragments)
            q['question_text'] = sanitize_question_text(q.get('question_text'))

            # image_urlの正規化（空文字/Noneを排除し、パスを整形）
            q['image_url'] = normalize_media_value(q.get('image_url'))

            # choicesをJSONから辞書へ
            if isinstance(q.get('choices'), str):
                try:
                    q['choices'] = json.loads(q['choices'])
                except Exception:
                    q['choices'] = {}

            # choice_imagesの後方互換
            if isinstance(q.get('choice_images'), str):
                try:
                    q['choice_images'] = json.loads(q['choice_images'])
                except Exception:
                    q['choice_images'] = None

            # 選択肢の各値を整形（画像パス等をサニタイズ）
            if isinstance(q.get('choices'), dict):
                cleaned_choices = {}
                for ck, cv in q['choices'].items():
                    cleaned_val = normalize_choice_value(cv)
                    if cleaned_val:
                        cleaned_choices[ck] = cleaned_val
                q['choices'] = cleaned_choices

            matched_questions.append(q)

        if not matched_questions:
            flash('指定された年度・期の問題が見つかりません', 'error')
            return redirect(url_for('exam.mock_exam'))

        # 画像選択肢フラグを追加
        matched_questions = add_image_choice_flags(matched_questions)

        # 試験セッションIDを生成
        exam_session_id = str(uuid.uuid4())

        # メモリに保存（セッションではなく）
        exam_sessions[exam_session_id] = {
            'questions': matched_questions,
            'user_id': session.get('user_id')
        }

        # セッションにはIDだけ保存
        session['exam_session_id'] = exam_session_id
        session.modified = True

        print(f"📚 Created exam session: {exam_session_id} with {len(matched_questions)} questions")

        exam_info = {
            'year': year,
            'season': season_display,
            'display_name': f"{year}年度 {season_display}",
            'exam_code': normalized_code
        }

        return render_template('mock_exam_practice.html',
                             questions=matched_questions,
                             exam_info=exam_info,
                             exam_session_id=exam_session_id)

    except Exception as e:
        print(f"❌ Mock exam start error: {e}")
        import traceback
        traceback.print_exc()
        flash(f'模擬試験の準備に失敗しました: {str(e)}', 'error')
        return redirect(url_for('exam.mock_exam'))

@exam_bp.route('/mock_exam/submit', methods=['POST'])
@login_required
def submit_mock_exam():
    """模擬試験の採点"""
    try:
        data = request.get_json()
        answers = data.get('answers', {})
        exam_session_id = data.get('exam_session_id')
        
        print(f"📝 Received answers: {len(answers)} questions")
        print(f"📊 Exam session ID: {exam_session_id}")
        
        # メモリから問題を取得
        if not exam_session_id or exam_session_id not in exam_sessions:
            print(f"❌ No exam session found for ID: {exam_session_id}")
            return jsonify({'error': '試験セッションが見つかりません。ページを再読み込みして試験を再開してください。'}), 400
        
        exam_data = exam_sessions[exam_session_id]
        questions = exam_data['questions']
        
        print(f"📚 Questions from session: {len(questions)}")
        
        # 採点処理
        total_count = len(questions)
        correct_count = 0
        details = []
        
        for i, question in enumerate(questions):
            question_index = str(i)
            user_answer = answers.get(question_index)
            correct_answer = question.get('correct_answer')
            is_correct = bool(user_answer and user_answer == correct_answer)

            if is_correct:
                correct_count += 1

            details.append({
                'index': i + 1,
                'question_id': question.get('question_id') or question.get('id'),
                'question_text': question.get('question_text'),
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'explanation': question.get('explanation'),
                'image_url': question.get('image_url'),
                'choices': question.get('choices', {})
            })
        
        score = round((correct_count / total_count) * 100, 1) if total_count > 0 else 0
        
        # 試験セッションを削除
        del exam_sessions[exam_session_id]
        session.pop('exam_session_id', None)
        
        print(f"✅ Result: {correct_count}/{total_count} = {score}%")
        
        return jsonify({
            'score': score,
            'correct_count': correct_count,
            'total_count': total_count,
            'details': details
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'採点処理中にエラー: {str(e)}'}), 500
