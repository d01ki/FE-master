#!/usr/bin/env python3
"""
基本情報技術者試験 過去問スクレイピングスクリプト

注意：
- このスクリプトは教育・学習目的のサンプルです
- 実際に使用する場合は、対象サイトの利用規約を必ず確認してください
- robots.txtを確認し、スクレイピングが許可されているか確認してください
- サーバーに負荷をかけないよう、適切な間隔でリクエストしてください
"""

import sys
import os
import time
import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.problem import Problem
from app.services.similarity import update_problem_embedding

class FEKakomonScraper:
    """
    基本情報技術者試験過去問スクレイパー
    
    注意：実際の利用前に以下を確認してください：
    1. 対象サイトの利用規約
    2. robots.txt
    3. 著作権情報
    4. サーバー負荷への配慮
    """
    
    def __init__(self, base_url: str, delay: float = 2.0):
        self.base_url = base_url
        self.delay = delay  # リクエスト間隔（秒）
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FE-Master Educational Scraper (https://github.com/d01ki/FE-master)'
        })
    
    def check_robots_txt(self) -> bool:
        """
robots.txtを確認してスクレイピングが許可されているかチェック
        """
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            response = self.session.get(robots_url, timeout=10)
            if response.status_code == 200:
                print(f"robots.txt found: {robots_url}")
                print("Please check if scraping is allowed for your use case.")
                print(response.text[:500])  # 最初の500文字を表示
                return True
        except Exception as e:
            print(f"Could not fetch robots.txt: {e}")
        return False
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """
ページのHTMLコンテンツを取得
        """
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # レスポンスの文字エンコーディングを適切に設定
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.content, 'html.parser')
            time.sleep(self.delay)  # サーバー負荷軽減
            return soup
            
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_problem_from_html(self, soup: BeautifulSoup, url: str) -> Optional[Dict]:
        """
HTMLから問題情報を抽出（サイト固有の実装が必要）
        """
        # この関数は対象サイトの構造に応じてカスタマイズが必要
        # 以下は一般的な構造の例
        
        try:
            problem_data = {
                'source': 'FE',
                'url': url,
                'text_md': '',
                'choices_json': {},
                'answer_index': 0,
                'explanation_md': '',
                'tags': [],
                'category': '',
                'difficulty': 0.5
            }
            
            # タイトルから年度・回・問題番号を抽出
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                # 例: "令和5年度 秋期 基本情報技術者試験 問1" のような形式を想定
                year_match = re.search(r'令和(\d+)年度', title_text)
                season_match = re.search(r'(春期|秋期)', title_text)
                question_match = re.search(r'問(\d+)', title_text)
                
                if year_match:
                    # 令和年を西暦に変換（令和1年=2019年）
                    reiwa_year = int(year_match.group(1))
                    problem_data['year'] = 2018 + reiwa_year
                
                if season_match:
                    season = season_match.group(1)
                    problem_data['exam_session'] = 'spring' if season == '春期' else 'autumn'
                
                if question_match:
                    problem_data['question_no'] = f"Q{question_match.group(1)}"
            
            # 問題文を抽出
            question_div = soup.find('div', class_=['question', 'problem', 'mondai'])
            if question_div:
                problem_data['text_md'] = self._html_to_markdown(question_div)
            
            # 選択肢を抽出
            choices_div = soup.find('div', class_=['choices', 'options', 'sentakushi'])
            if choices_div:
                choices = {}
                choice_items = choices_div.find_all(['li', 'div'], class_=['choice', 'option'])
                
                for i, choice in enumerate(choice_items):
                    choice_text = choice.get_text(strip=True)
                    # "ア. 選択肢の内容" のような形式から選択肢を抽出
                    choice_match = re.match(r'^[ア-エa-d\.\)\s]*(.*)', choice_text)
                    if choice_match:
                        choice_key = chr(ord('a') + i)  # a, b, c, d
                        choices[choice_key] = choice_match.group(1).strip()
                
                problem_data['choices_json'] = choices
            
            # 正解を抽出
            answer_div = soup.find('div', class_=['answer', 'correct', 'seikai'])
            if answer_div:
                answer_text = answer_div.get_text()
                answer_match = re.search(r'[ア-エ]', answer_text)
                if answer_match:
                    # カタカナをアルファベットのインデックスに変換
                    katakana_to_index = {'ア': 0, 'イ': 1, 'ウ': 2, 'エ': 3}
                    problem_data['answer_index'] = katakana_to_index.get(answer_match.group(), 0)
            
            # 解説を抽出
            explanation_div = soup.find('div', class_=['explanation', 'kaisetsu'])
            if explanation_div:
                problem_data['explanation_md'] = self._html_to_markdown(explanation_div)
            
            # カテゴリーを抽出
            category_elem = soup.find(['span', 'div'], class_=['category', 'bunrui'])
            if category_elem:
                problem_data['category'] = category_elem.get_text(strip=True)
            
            return problem_data
            
        except Exception as e:
            print(f"Error extracting problem from {url}: {e}")
            return None
    
    def _html_to_markdown(self, element) -> str:
        """
HTMLをMarkdownに変換
        """
        if not element:
            return ''
        
        # 簡単なHTML→Markdown変換
        text = element.get_text(separator='\n', strip=True)
        
        # 基本的な変換ルール
        # より高度な変換が必要な場合はhtml2textライブラリを使用
        text = re.sub(r'\n\s*\n', '\n\n', text)  # 複数の改行を整理
        
        return text
    
    def scrape_problem_urls(self, index_url: str) -> List[str]:
        """
問題一覧ページから個別問題のURLを取得
        """
        soup = self.get_page_content(index_url)
        if not soup:
            return []
        
        urls = []
        
        # 問題へのリンクを抽出（サイト構造に依存）
        # 例：<a href="/problem/2023/autumn/q01">問1</a>
        problem_links = soup.find_all('a', href=re.compile(r'/(problem|question|mondai)/'))
        
        for link in problem_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                urls.append(full_url)
        
        return urls
    
    def scrape_problems(self, start_url: str, max_problems: int = 10) -> List[Dict]:
        """
問題を一括スクレイピング
        """
        print(f"Starting to scrape problems from: {start_url}")
        print(f"Max problems to scrape: {max_problems}")
        
        # robots.txtチェック
        self.check_robots_txt()
        
        problems = []
        
        # 問題URLリストを取得
        problem_urls = self.scrape_problem_urls(start_url)
        
        if not problem_urls:
            print("No problem URLs found. Please check the site structure.")
            return []
        
        print(f"Found {len(problem_urls)} problem URLs")
        
        # 各問題をスクレイピング
        for i, url in enumerate(problem_urls[:max_problems]):
            print(f"\nScraping problem {i+1}/{min(len(problem_urls), max_problems)}")
            
            soup = self.get_page_content(url)
            if soup:
                problem_data = self.extract_problem_from_html(soup, url)
                if problem_data and self._validate_problem_data(problem_data):
                    problems.append(problem_data)
                    print(f"Successfully extracted problem: {problem_data.get('question_no', 'Unknown')}")
                else:
                    print(f"Failed to extract valid problem data from {url}")
        
        return problems
    
    def _validate_problem_data(self, data: Dict) -> bool:
        """
問題データの妥当性をチェック
        """
        required_fields = ['text_md', 'choices_json', 'answer_index']
        
        for field in required_fields:
            if not data.get(field):
                print(f"Missing required field: {field}")
                return False
        
        if not isinstance(data.get('choices_json'), dict) or len(data['choices_json']) < 2:
            print("Invalid choices_json: must be a dict with at least 2 choices")
            return False
        
        if not isinstance(data.get('answer_index'), int) or data['answer_index'] < 0:
            print("Invalid answer_index: must be a non-negative integer")
            return False
        
        return True

def save_problems_to_database(problems: List[Dict], db: Session) -> int:
    """
取得した問題をデータベースに保存
    """
    saved_count = 0
    
    for problem_data in problems:
        try:
            # 重複チェック
            existing = db.query(Problem).filter(
                Problem.source == problem_data.get('source', 'FE'),
                Problem.year == problem_data.get('year'),
                Problem.exam_session == problem_data.get('exam_session'),
                Problem.question_no == problem_data.get('question_no')
            ).first()
            
            if existing:
                print(f"Problem already exists: {problem_data.get('question_no')}")
                continue
            
            # 新しい問題を作成
            problem = Problem(
                source=problem_data.get('source', 'FE'),
                year=problem_data.get('year', 2023),
                exam_session=problem_data.get('exam_session', 'unknown'),
                question_no=problem_data.get('question_no', 'Q?'),
                text_md=problem_data['text_md'],
                choices_json=problem_data['choices_json'],
                answer_index=problem_data['answer_index'],
                explanation_md=problem_data.get('explanation_md', ''),
                tags=problem_data.get('tags', []),
                category=problem_data.get('category'),
                difficulty=problem_data.get('difficulty', 0.5)
            )
            
            db.add(problem)
            db.commit()
            db.refresh(problem)
            
            # 埋め込み生成
            try:
                update_problem_embedding(db, problem)
                print(f"Saved problem with embedding: {problem.question_no}")
            except Exception as e:
                print(f"Saved problem but failed to generate embedding: {e}")
            
            saved_count += 1
            
        except Exception as e:
            print(f"Error saving problem {problem_data.get('question_no')}: {e}")
            db.rollback()
    
    return saved_count

def main():
    """
メイン実行関数
    """
    print("FE Kakomon Scraper")
    print("="*50)
    print("WARNING: This is a sample implementation for educational purposes.")
    print("Before using this scraper:")
    print("1. Check the target site's Terms of Service")
    print("2. Check robots.txt")
    print("3. Respect copyright and server resources")
    print("4. Consider using official APIs if available")
    print("="*50)
    
    # 使用例（実際のURLは適切なものに置き換えてください）
    # この例は架空のURLです
    base_url = "https://example-kakomon-site.com"
    start_url = f"{base_url}/fe/problems/2023/autumn"
    
    # ユーザー確認
    response = input("Do you want to proceed with scraping? (y/N): ")
    if response.lower() != 'y':
        print("Scraping cancelled.")
        return
    
    # スクレイパー初期化
    scraper = FEKakomonScraper(base_url, delay=3.0)  # 3秒間隔
    
    # 問題をスクレイピング
    problems = scraper.scrape_problems(start_url, max_problems=5)
    
    if problems:
        print(f"\nSuccessfully scraped {len(problems)} problems")
        
        # データベースに保存
        db = SessionLocal()
        try:
            saved_count = save_problems_to_database(problems, db)
            print(f"Saved {saved_count} problems to database")
        finally:
            db.close()
    else:
        print("No problems were scraped")

if __name__ == "__main__":
    main()
