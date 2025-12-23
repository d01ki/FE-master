import types

from app.core.question_manager import QuestionManager


class DummyDB:
    def __init__(self, db_type):
        self.db_type = db_type
        self.captured_query = None
        self.captured_params = None
        self.next_result = []

    def execute_query(self, query, params=None):
        self.captured_query = query
        self.captured_params = params or ()
        return self.next_result


def test_random_query_uses_rand_for_mysql():
    db = DummyDB(db_type="mysql")
    qm = QuestionManager(db)
    db.next_result = [{"id": 1, "choices": "{}", "question_id": "q1", "question_text": "t", "correct_answer": "A", "explanation": "", "image_url": None, "choice_images": None, "genre": None}]

    qm.get_random_question()

    assert "RAND()" in db.captured_query
    assert "RANDOM()" not in db.captured_query


def test_random_query_uses_random_for_sqlite():
    db = DummyDB(db_type="sqlite")
    qm = QuestionManager(db)
    db.next_result = [{"id": 1, "choices": "{}", "question_id": "q1", "question_text": "t", "correct_answer": "A", "explanation": "", "image_url": None, "choice_images": None, "genre": None}]

    qm.get_random_question()

    assert "RANDOM()" in db.captured_query
    assert "RAND()" not in db.captured_query
