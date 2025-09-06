"""
PDF処理ユーティリティ
IPA公開問題のPDFから問題データを抽出し、JSON形式に変換
"""

import re
import json
from typing import List, Dict, Optional
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

class PDFProcessor:
    """PDF問題集の処理クラス"""
    
    def __init__(self):
        # 問題パターンの正規表現
        self.question_pattern = re.compile(r'問(\d+)[\s　]*(.+?)(?=問\d+|$)', re.DOTALL)
        self.choice_pattern = re.compile(r'([アイウエ])[\s　]*(.+?)(?=[アイウエ]|解答|解説|$)', re.DOTALL)
        self.answer_pattern = re.compile(r'解答[\s　]*[：:][\s　]*([アイウエ])', re.IGNORECASE)
        self.explanation_pattern = re.compile(r'解説[\s　]*[：:][\s　]*(.+?)(?=問\d+|$)', re.DOTALL | re.IGNORECASE)
        
    def extract_questions_from_pdf(self, pdf_path: str) -> List[Dict]:
        """PDFファイルから問題を抽出"""
        if pdfplumber:
            return self._extract_with_pdfplumber(pdf_path)
        elif PyPDF2:
            return self._extract_with_pypdf2(pdf_path)
        else:
            raise ImportError("PDF処理ライブラリ（pdfplumber または PyPDF2）がインストールされていません")
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> List[Dict]:
        """pdfplumberを使用してPDFから文字列を抽出"""
        questions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        questions = self._parse_questions_from_text(full_text)
        return questions
    
    def _extract_with_pypdf2(self, pdf_path: str) -> List[Dict]:
        """PyPDF2を使用してPDFから文字列を抽出"""
        questions = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = ""
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        questions = self._parse_questions_from_text(full_text)
        return questions
    
    def _parse_questions_from_text(self, text: str) -> List[Dict]:
        """抽出したテキストから問題を解析"""
        questions = []
        
        # 問題ごとに分割
        question_matches = self.question_pattern.findall(text)
        
        for i, (question_num, question_content) in enumerate(question_matches):
            try:
                question_data = self._parse_single_question(question_num, question_content)
                if question_data:
                    questions.append(question_data)
            except Exception as e:
                print(f"問題{question_num}の解析中にエラーが発生しました: {e}")
                continue
        
        return questions
    
    def _parse_single_question(self, question_num: str, content: str) -> Optional[Dict]:
        """単一問題の解析"""
        # 問題文の抽出（選択肢の前まで）
        choice_start = re.search(r'[アイウエ][\s　]*', content)
        if not choice_start:
            return None
        
        question_text = content[:choice_start.start()].strip()
        choices_and_answer = content[choice_start.start():]
        
        # 選択肢の抽出
        choices = self._extract_choices(choices_and_answer)
        if not choices or len(choices) < 2:
            return None
        
        # 正解の抽出
        correct_answer = self._extract_correct_answer(choices_and_answer)
        if not correct_answer:
            return None
        
        # 解説の抽出
        explanation = self._extract_explanation(choices_and_answer)
        
        # ジャンル推定（キーワードベース）
        genre = self._estimate_genre(question_text)
        
        return {
            "question_id": f"Q{question_num.zfill(3)}",
            "question_text": self._clean_text(question_text),
            "choices": choices,
            "correct_answer": correct_answer,
            "explanation": self._clean_text(explanation) if explanation else "",
            "genre": genre
        }
    
    def _extract_choices(self, text: str) -> Dict[str, str]:
        """選択肢の抽出"""
        choices = {}
        choice_matches = self.choice_pattern.findall(text)
        
        for choice_letter, choice_text in choice_matches:
            clean_choice = self._clean_text(choice_text)
            if clean_choice and len(clean_choice.strip()) > 0:
                choices[choice_letter] = clean_choice
        
        return choices
    
    def _extract_correct_answer(self, text: str) -> Optional[str]:
        """正解の抽出"""
        answer_match = self.answer_pattern.search(text)
        return answer_match.group(1) if answer_match else None
    
    def _extract_explanation(self, text: str) -> Optional[str]:
        """解説の抽出"""
        explanation_match = self.explanation_pattern.search(text)
        return explanation_match.group(1) if explanation_match else None
    
    def _clean_text(self, text: str) -> str:
        """テキストのクリーニング"""
        if not text:
            return ""
        
        # 不要な空白や改行を除去
        cleaned = re.sub(r'\s+', ' ', text.strip())
        cleaned = re.sub(r'[　]+', ' ', cleaned)  # 全角スペースを半角に
        
        return cleaned
    
    def _estimate_genre(self, question_text: str) -> str:
        """問題文からジャンルを推定"""
        genre_keywords = {
            "ハードウェア": ["CPU", "メモリ", "キャッシュ", "プロセッサ", "コンピュータ", "ハードウェア", "ハードディスク", "SSD", "RAM", "ROM", "BIOS"],
            "ソフトウェア": ["OS", "オペレーティングシステム", "プログラム", "アプリケーション", "ソフトウェア", "Windows", "Linux", "ファイルシステム", "プロセス"],
            "データベース": ["データベース", "SQL", "テーブル", "正規化", "DBMS", "関係", "SELECT", "INSERT", "UPDATE", "DELETE", "主キー", "外部キー"],
            "ネットワーク": ["ネットワーク", "TCP", "IP", "プロトコル", "LAN", "WAN", "インターネット", "HTTP", "FTP", "DNS", "ルータ", "スイッチ"],
            "セキュリティ": ["セキュリティ", "暗号", "認証", "ファイアウォール", "ウイルス", "マルウェア", "脆弱性", "SSL", "TLS", "ハッシュ"],
            "プログラミング": ["プログラミング", "アルゴリズム", "データ構造", "関数", "変数", "配列", "ループ", "条件分岐", "オブジェクト指向", "Java", "Python", "C言語"],
            "システム開発": ["システム開発", "要件定義", "設計", "テスト", "プロジェクト", "工程", "ウォーターフォール", "アジャイル", "UML", "開発手法"],
            "マネジメント": ["プロジェクトマネジメント", "品質管理", "リスク管理", "コスト", "スケジュール", "PMBOK", "工程管理", "進捗管理"]
        }
        
        for genre, keywords in genre_keywords.items():
            for keyword in keywords:
                if keyword in question_text:
                    return genre
        
        return "その他"
    
    def create_sample_questions(self) -> List[Dict]:
        """サンプル問題を作成（テスト用）"""
        sample_questions = [
            {
                "question_id": "Q001",
                "question_text": "コンピュータのCPUが1秒間に実行できる命令数を表す指標は何か。",
                "choices": {
                    "ア": "クロック周波数",
                    "イ": "MIPS（Million Instructions Per Second）",
                    "ウ": "キャッシュサイズ",
                    "エ": "メモリ容量"
                },
                "correct_answer": "イ",
                "explanation": "MIPS（Million Instructions Per Second）は、CPUが1秒間に実行できる命令数を百万単位で表した性能指標です。クロック周波数は動作速度を表しますが、命令実行数とは異なります。",
                "genre": "ハードウェア"
            },
            {
                "question_id": "Q002",
                "question_text": "関係データベースにおいて、テーブル間の関連を表現するために使用されるキーは何か。",
                "choices": {
                    "ア": "主キー（Primary Key）",
                    "イ": "外部キー（Foreign Key）",
                    "ウ": "候補キー（Candidate Key）",
                    "エ": "複合キー（Composite Key）"
                },
                "correct_answer": "イ",
                "explanation": "外部キーは、他のテーブルの主キーを参照することで、テーブル間の関連を表現するキーです。主キーは各テーブル内でレコードを一意に識別するためのものです。",
                "genre": "データベース"
            },
            {
                "question_id": "Q003",
                "question_text": "TCP/IPプロトコルスイートにおいて、信頼性のあるデータ転送を提供するプロトコルは何か。",
                "choices": {
                    "ア": "UDP（User Datagram Protocol）",
                    "イ": "IP（Internet Protocol）",
                    "ウ": "TCP（Transmission Control Protocol）",
                    "エ": "HTTP（HyperText Transfer Protocol）"
                },
                "correct_answer": "ウ",
                "explanation": "TCP（Transmission Control Protocol）は、データの確実な配送を保証する信頼性のあるプロトコルです。UDPは高速ですが信頼性がなく、IPは経路制御、HTTPはWebアプリケーション層のプロトコルです。",
                "genre": "ネットワーク"
            },
            {
                "question_id": "Q004",
                "question_text": "プログラムにおいて、同じ処理を繰り返し実行するための制御構造は何か。",
                "choices": {
                    "ア": "順次処理",
                    "イ": "条件分岐",
                    "ウ": "反復処理（ループ処理）",
                    "エ": "関数呼び出し"
                },
                "correct_answer": "ウ",
                "explanation": "反復処理（ループ処理）は、同じ処理を条件が満たされる間繰り返し実行する制御構造です。for文やwhile文などがこれに該当します。",
                "genre": "プログラミング"
            },
            {
                "question_id": "Q005",
                "question_text": "情報セキュリティの三大要素として正しい組み合わせはどれか。",
                "choices": {
                    "ア": "機密性、完全性、可用性",
                    "イ": "機密性、安全性、利便性",
                    "ウ": "秘匿性、正確性、効率性",
                    "エ": "プライバシー、セキュリティ、ユーザビリティ"
                },
                "correct_answer": "ア",
                "explanation": "情報セキュリティの三大要素は、機密性（Confidentiality）、完全性（Integrity）、可用性（Availability）です。これらの頭文字を取ってCIAとも呼ばれます。",
                "genre": "セキュリティ"
            }
        ]
        
        return sample_questions
    
    def create_extended_sample_questions(self) -> List[Dict]:
        """拡張サンプル問題を作成（10問）"""
        extended_questions = [
            {
                "question_id": "Q006",
                "question_text": "2進数の11010101を10進数に変換した値はどれか。",
                "choices": {
                    "ア": "213",
                    "イ": "214", 
                    "ウ": "215",
                    "エ": "216"
                },
                "correct_answer": "ア",
                "explanation": "2進数11010101は、1×128 + 1×64 + 0×32 + 1×16 + 0×8 + 1×4 + 0×2 + 1×1 = 128+64+16+4+1 = 213となります。",
                "genre": "ハードウェア"
            },
            {
                "question_id": "Q007",
                "question_text": "SQLのSELECT文において、重複する行を除いて結果を表示するために使用するキーワードはどれか。",
                "choices": {
                    "ア": "UNIQUE",
                    "イ": "DISTINCT",
                    "ウ": "DIFFERENT",
                    "エ": "SINGLE"
                },
                "correct_answer": "イ",
                "explanation": "DISTINCTキーワードは、SELECT文の結果から重複する行を除いて表示するために使用されます。例：SELECT DISTINCT column_name FROM table_name;",
                "genre": "データベース"
            },
            {
                "question_id": "Q008",
                "question_text": "OSI参照モデルの第4層（トランスポート層）の主な機能は何か。",
                "choices": {
                    "ア": "データの暗号化",
                    "イ": "エラー検出と訂正",
                    "ウ": "エンドツーエンドの信頼性のある通信",
                    "エ": "物理的な信号の変換"
                },
                "correct_answer": "ウ",
                "explanation": "トランスポート層（第4層）は、エンドツーエンドの信頼性のある通信を提供します。TCPやUDPなどのプロトコルがこの層で動作し、データの分割・組立や順序制御を行います。",
                "genre": "ネットワーク"
            },
            {
                "question_id": "Q009",
                "question_text": "配列の要素を順番に検索して目的の値を見つけるアルゴリズムは何か。",
                "choices": {
                    "ア": "線形探索（リニアサーチ）",
                    "イ": "二分探索（バイナリサーチ）",
                    "ウ": "ハッシュ探索",
                    "エ": "木探索"
                },
                "correct_answer": "ア",
                "explanation": "線形探索（リニアサーチ）は、配列の先頭から順番に要素を調べて目的の値を見つけるアルゴリズムです。時間計算量はO(n)です。",
                "genre": "プログラミング"
            },
            {
                "question_id": "Q010",
                "question_text": "公開鍵暗号方式の特徴として正しいものはどれか。",
                "choices": {
                    "ア": "暗号化と復号化に同じ鍵を使用する",
                    "イ": "暗号化に公開鍵、復号化に秘密鍵を使用する",
                    "ウ": "鍵の配布が困難である",
                    "エ": "対称鍵暗号より処理速度が速い"
                },
                "correct_answer": "イ",
                "explanation": "公開鍵暗号方式では、暗号化に公開鍵、復号化に秘密鍵（私有鍵）を使用します。これにより、鍵配布問題を解決できますが、処理速度は対称鍵暗号より遅いです。",
                "genre": "セキュリティ"
            }
        ]
        
        return extended_questions
