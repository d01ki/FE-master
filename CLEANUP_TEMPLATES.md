## 不要なHTMLファイルを削除しました

以下の不要なテンプレートファイルを削除:

### 削除したファイル
- templates/404.html (error.htmlで代替)
- templates/home.html (未使用)  
- templates/index.html (dashboard.htmlで代替)
- templates/login.html (auth/login.htmlで代替)
- templates/register.html (auth/register.htmlで代替)
- templates/problem.html (question.htmlで代替)
- templates/problem_list.html (未使用)
- templates/problems/ (未使用ディレクトリ)

### 保持したファイル
- templates/base.html ✅
- templates/dashboard.html ✅
- templates/admin.html ✅
- templates/admin_login.html ✅
- templates/error.html ✅
- templates/question.html ✅
- templates/practice.html ✅
- templates/genre_practice.html ✅
- templates/mock_exam_select.html ✅
- templates/mock_exam_practice.html ✅
- templates/history.html ✅
- templates/auth/login.html ✅
- templates/auth/register.html ✅

これでプロジェクトが整理され、app.pyで実際に使用されているテンプレートのみが残りました。
