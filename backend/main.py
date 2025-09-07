from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

app = FastAPI(title="基本情報技術者試験 学習アプリ")

# 静的ファイルとテンプレートの設定
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

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
    
    return templates.TemplateResponse(
        "problem.html",
        {
            "request": request,
            "current_user": None,
            "problem": problem,
            "show_answer": False,
            "user_answer": None,
            "related_problems": [p for p in sample_problems if p["id"] != problem_id]
        }
    )
