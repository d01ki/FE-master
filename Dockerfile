FROM python:3.11-slim

# ビルドに必要な最小限のツールをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先にライブラリをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# その後にアプリ本体をコピー
COPY . .

# 実行
ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]
