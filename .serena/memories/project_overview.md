# Project Overview
FE Master is a learning application for the "Fundamental Information Technology Engineer Examination" (FE Exam) in Japan.

## Tech Stack
- **Backend**: Python 3.11+, Flask 2.3+
- **Database**: PostgreSQL 15+ (Production) or SQLite (Dev/Default)
- **Frontend**: HTML5, JavaScript, Tailwind CSS (via CDN)
- **Infrastructure**: Docker, Docker Compose

## Core Structure
- `app/`: Main application package
  - `core/`: Core modules (Auth, DB, Config)
  - `routes/`: Blueprint definitions (Routes)
  - `templates/`: Jinja2 templates
  - `static/`: Static files
- `app.py`: Application entry point (Factory Pattern)
- `tests/`: Test suite