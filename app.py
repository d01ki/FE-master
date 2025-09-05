from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response
from starlette.requests import Request

def flash(request: Request, message: str, category: str = "info"):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append({"message": message, "category": category})

def get_flashed_messages(request: Request = None, with_categories: bool = False):
    if request is None:
        return []
    messages = request.session.pop("_messages") if "_messages" in request.session else []
    if with_categories:
        return [(msg["category"], msg["message"]) for msg in messages]
    return [msg["message"] for msg in messages]

app = FastAPI(title="基本情報技術者試験 学習アプリ", debug=True)

# Jinja2テンプレートの設定
templates = Jinja2Templates(directory="templates")

async def flash_messages(with_categories=False):
    def inner(request):
        return get_flashed_messages(request, with_categories)
    return inner

# テンプレートグローバル変数の設定
templates.env.globals.update({
    'get_messages': flash_messages,
})
@app.middleware("http")
async def add_template_context(request: Request, call_next):
    response = await call_next(request)
    if isinstance(response, Response):
        response.context = {
            "request": request
        }
    return response

# セッション管理の設定
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory="static"), name="static")

# テンプレートの設定
templates = Jinja2Templates(directory="templates")
templates.env.globals.update({
    'get_flashed_messages': get_flashed_messages
})

# サンプル問題データ
sample_problems = [
    {
        "id": 1,
        "category": "基礎理論",
        "exam_year": 2024,
        "description": "次の論理式で、真となるものはどれか。",
        "options": [
            "A AND (NOT A)",
            "A OR (NOT A)",
            "A AND A",
            "NOT (A OR B) AND (A AND B)"
        ],
        "correct_answer": 2,
        "explanation": "A OR (NOT A) は常に真となります（排中律）。",
        "estimated_time": 2
    },
    {
        "id": 2,
        "category": "データベース",
        "exam_year": 2024,
        "description": "RDBMSにおけるトランザクションの特性として、不適切なものはどれか。",
        "options": [
            "Atomicity（原子性）",
            "Consistency（一貫性）",
            "Parallelism（並列性）",
            "Durability（永続性）"
        ],
        "correct_answer": 3,
        "explanation": "トランザクションのACID特性は、Atomicity（原子性）、Consistency（一貫性）、Isolation（独立性）、Durability（永続性）です。",
        "estimated_time": 3
    }
]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # テスト用のフラッシュメッセージ
    flash(request, "ようこそ！FE学習アプリへ", "info")
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": None,
            "total_questions": len(sample_problems),
            "solved_questions": 0,
            "overall_progress": 0,
            "accuracy_rate": 0,
            "recent_activities": [],
            "categories": [
                {"name": "basic", "display_name": "基礎理論", "icon": "fa-microchip", "progress": 0},
                {"name": "db", "display_name": "データベース", "icon": "fa-database", "progress": 0},
                {"name": "network", "display_name": "ネットワーク", "icon": "fa-network-wired", "progress": 0},
                {"name": "security", "display_name": "セキュリティ", "icon": "fa-shield-alt", "progress": 0}
            ]
        }
    )

@app.get("/problems", response_class=HTMLResponse)
async def problem_list(request: Request):
    return templates.TemplateResponse(
        "problem_list.html",
        {
            "request": request,
            "current_user": None,
            "problems": sample_problems,
            "categories": [
                {"name": "basic", "display_name": "基礎理論"},
                {"name": "db", "display_name": "データベース"},
                {"name": "network", "display_name": "ネットワーク"},
                {"name": "security", "display_name": "セキュリティ"}
            ]
        }
    )

@app.get("/problem/{problem_id}", response_class=HTMLResponse)
async def problem_detail(request: Request, problem_id: int):
    problem = next((p for p in sample_problems if p["id"] == problem_id), None)
    if problem is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    # セッションから解答履歴を取得
    user_answers = request.session.get("user_answers", {})
    show_answer = str(problem_id) in user_answers
    user_answer = user_answers.get(str(problem_id))
    
    return templates.TemplateResponse(
        "problem.html",
        {
            "request": request,
            "current_user": None,
            "problem": problem,
            "show_answer": show_answer,
            "user_answer": user_answer,
            "related_problems": [p for p in sample_problems if p["id"] != problem_id]
        }
    )

@app.post("/problem/{problem_id}/answer")
async def submit_answer(request: Request, problem_id: int, answer: int = Form(...)):
    problem = next((p for p in sample_problems if p["id"] == problem_id), None)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # 解答を保存
    user_answers = request.session.get("user_answers", {})
    user_answers[str(problem_id)] = answer
    request.session["user_answers"] = user_answers
    
    # 正誤判定
    is_correct = answer == problem["correct_answer"]
    
    # 解答履歴を保存
    history = request.session.get("history", [])
    history.append({
        "problem_id": problem_id,
        "answer": answer,
        "is_correct": is_correct,
        "timestamp": str(datetime.now())
    })
    request.session["history"] = history
    
    return RedirectResponse(
        url=f"/problem/{problem_id}",
        status_code=303
    )
