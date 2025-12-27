import sys
import os
sys.path.insert(0, os.getcwd())

import importlib.util
spec = importlib.util.spec_from_file_location("app_root", "app.py")
app_root = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_root)
create_app = app_root.create_app

from app.core.database import db_manager
from app.core.question_manager import QuestionManager


app = create_app()
print(f"App Root Path: {app.root_path}")
with app.app_context():
    qm = QuestionManager(db_manager)
    questions = qm.get_all_questions()
    print(f"Total questions: {len(questions)}")
    for q in questions:
        img_url = q.get('image_url')
        if img_url:
            print(f"ID: {q.get('id') or q.get('question_id')}, Image: {img_url}")
            # Check if file exists on disk
            fname = os.path.basename(img_url)
            fpath = os.path.join(os.getcwd(), 'protected_images', 'questions', fname)
            print(f"  Path: {fpath}, Exists: {os.path.exists(fpath)}")
