import requests
from bs4 import BeautifulSoup
# from openai import OpenAI # <--- openai パッケージは不要になります
import time
import random
from datetime import datetime, timedelta
import re
from urllib.parse import quote
import json
from colorama import Fore, Style, init

# カラー出力の初期化
init(autoreset=True)

class RealTimeNewsAnalyzer:
    def __init__(self, openrouter_api_key):
        # self.client = OpenAI(...) # <--- この行を削除
        self.openrouter_api_key = openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.target_companies = [
            "XIAOMI", "SEMICONDUCTOR MANUFACTURING", "BYD CO LTD-H", 
            "ALIBABA", "NETEASE", "TENCENT", "TRIP.COM", 
            "LI AUTO CLASS", "BAIDU", "MEITUAN"
        ]
        self.global_analysis_results = []
        self.china_analysis_results = []
        
    def colored_print(self, text, color=Fore.WHITE, style=Style.NORMAL):
        """カラー出力用のヘルパー関数"""
        print(f"{style}{color}{text}{Style.RESET_ALL}")
        
    def search_google_news_single(self, query, max_results=25):
        """単一クエリでGoogle Newsから記事を取得"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,ja;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        base_url = "https://news.google.com/search"
        params = {
            'q': query,
            'hl': 'en-US',
            'gl': 'US',
            'ceid': 'US:en'
        }
        
        try:
            self.colored_print(f"🔍 検索実行: \"{query}\"", Fore.CYAN, Style.BRIGHT)
            response = requests.get(base_url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article')
            
            self.colored_print(f"📰 発見された記事数: {len(articles)}", Fore.YELLOW)
            
            news_items = []
            one_week_ago = datetime.now() - timedelta(days=7)
            
            for i, article in enumerate(articles[:max_results]):
                try:
                    # タイトル取得（複数のセレクタを試行）
                    title = ""
                    title_selectors = ['a.JtKRv', 'a[data-n-au]', 'h3 a', 'h4 a', 'article a']
                    for selector in title_selectors:
                        title_tag = article.select_one(selector)
                        if title_tag and title_tag.get_text(strip=True):
                            title = title_tag.get_text(strip=True)
                            break
                    
                    if not title:
                        continue
                    
                    # リンク取得
                    link = ""
                    link_selectors = ['a.WwrzSb', 'a.JtKRv', 'a[data-n-au]']
                    for selector in link_selectors:
                        link_tag = article.select_one(selector)
                        if link_tag and link_tag.get('href'):
                            link = link_tag['href']
                            if link.startswith('./'):
                                link = 'https://news.google.com' + link[1:]
                            elif link.startswith('/'):
                                link = 'https://news.google.com' + link
                            break
                    
                    # ソース取得
                    source = "Unknown"
                    source_selectors = ['div.vr1PYe', '.CEMjEf', 'span.vr1PYe']
                    for selector in source_selectors:
                        source_tag = article.select_one(selector)
                        if source_tag and source_tag.get_text(strip=True):
                            source = source_tag.get_text(strip=True)
                            break
                    
                    # 時間取得
                    time_text = "Unknown"
                    time_tag = article.select_one('time')
                    if time_tag:
                        time_text = time_tag.get_text(strip=True)
                    
                    # スニペット取得
                    snippet = ""
                    snippet_selectors = ['span.fCU_i', '.Rai5ob', '.xBjCHd', 'div[data-snippet]']
                    for selector in snippet_selectors:
                        snippet_tag = article.select_one(selector)
                        if snippet_tag and snippet_tag.get_text(strip=True):
                            snippet = snippet_tag.get_text(strip=True)
                            break
                    
                    # 日付推定
                    estimated_date = self._estimate_date_from_time_text(time_text)
                    
                    # 1週間以内かチェック
                    if estimated_date and estimated_date < one_week_ago:
                        continue
                    
                    news_item = {
                        'title': title,
                        'link': link,
                        'source': source,
                        'time': time_text,
                        'snippet': snippet,
                        'date': estimated_date.strftime('%Y/%m/%d') if estimated_date else 'Unknown',
                        'query': query
                    }
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    self.colored_print(f"記事{i+1}の処理エラー: {e}", Fore.RED)
                    continue
            
            self.colored_print(f"✅ 取得完了: {len(news_items)}件の記事", Fore.GREEN)
            
            # 取得した記事の一覧表示（最初の3件）
            for i, item in enumerate(news_items[:3], 1):
                self.colored_print(f"  {i}. {item['title'][:70]}...", Fore.WHITE)
                self.colored_print(f"    📅 {item['time']} | 🏢 {item['source']}", Fore.LIGHTBLACK_EX)
            
            if len(news_items) > 3:
                self.colored_print(f"    ... 他 {len(news_items) - 3} 件", Fore.LIGHTBLACK_EX)
            
            return news_items
            
        except requests.exceptions.RequestException as e:
            self.colored_print(f"❌ リクエストエラー: {e}", Fore.RED)
            return []
        except Exception as e:
            self.colored_print(f"❌ 予期せぬエラー: {e}", Fore.RED)
            return []

    def _estimate_date_from_time_text(self, time_text):
        """時間テキストから日付を推定"""
        if not time_text or time_text == "Unknown":
            return datetime.now()
        
        now = datetime.now()
        time_text_lower = time_text.lower()
        
        try:
            # 分単位
            if 'minute' in time_text_lower or 'min' in time_text_lower:
                minutes = re.search(r'(\d+)', time_text)
                if minutes:
                    return now - timedelta(minutes=int(minutes.group(1)))
            
            # 時間単位
            elif 'hour' in time_text_lower:
                hours = re.search(r'(\d+)', time_text)
                if hours:
                    return now - timedelta(hours=int(hours.group(1)))
            
            # 日単位
            elif 'day' in time_text_lower or 'yesterday' in time_text_lower:
                if 'yesterday' in time_text_lower:
                    return now - timedelta(days=1)
                days = re.search(r'(\d+)', time_text)
                if days:
                    return now - timedelta(days=int(days.group(1)))
            
            # 週単位
            elif 'week' in time_text_lower:
                weeks = re.search(r'(\d+)', time_text)
                if weeks:
                    return now - timedelta(weeks=int(weeks.group(1)))
    
        except Exception:
            pass
        
        return now

    def analyze_news_with_llm(self, news_data, query, analysis_type="global"):
        """LLMを使用してニュースを分析（最大15回のリトライ機能付き）"""
        if not news_data:
            return ""

        today = datetime.now().strftime("%Y/%m/%d")
        news_text = "\n".join([
            f"Date: {item['date']}\nTitle: {item['title']}\nSource: {item['source']}\nSnippet: {item['snippet']}\n---"
            for item in news_data
        ])

        if analysis_type == "global":
            prompt = self._create_global_analysis_prompt(today, query, news_text)
        else:
            prompt = self._create_china_analysis_prompt(today, query, news_text)

        max_retries = 15
        for attempt in range(max_retries):
            try:
                self.colored_print(f"🤖 LLM分析開始 (試行 {attempt + 1}/{max_retries}, クエリ: {query})", Fore.MAGENTA)

                # --- ▼▼▼ ここからが変更箇所 ▼▼▼ ---
                url = f"{self.base_url}/chat/completions"
                
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://realtime-news-analyzer.com", # 任意ヘッダー
                    "X-Title": "Real-time News Analyzer", # 任意ヘッダー
                }
                
                payload = {
                    "model": "mistralai/mistral-small",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.3
                }

                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status() # HTTPエラーがあれば例外を発生させる
                
                response_data = response.json()
                result = response_data['choices'][0]['message']['content']
                # --- ▲▲▲ ここまでが変更箇所 ▲▲▲ ---

                if len(result.strip()) <= 0:
                    raise ValueError(result)

                self.colored_print(f"✅ LLM分析完了 (クエリ: {query})", Fore.GREEN)
                return result # 成功したら結果を返してループを抜ける

            except Exception as e:
                # 最後のリトライでも失敗した場合
                if attempt + 1 == max_retries:
                    self.colored_print(f"❌ LLM分析が{max_retries}回すべて失敗しました (クエリ: {query}): {e}", Fore.RED, Style.BRIGHT)
                    return "" # 最終的に失敗したら空文字を返す
                
                # 次のリトライまでの待機時間を計算 (エクスポネンシャル・バックオフ + ジッター)
                # 2のべき乗で待機時間が増え、最大60秒に制限
                backoff_time = (2 ** attempt) + random.uniform(0, 1)
                sleep_time = min(backoff_time, 60)

                self.colored_print(f"⚠️  LLM分析エラー (試行 {attempt + 1}/{max_retries}): {e}", Fore.YELLOW)
                self.colored_print(f"⏳ {sleep_time:.1f}秒後に再試行します...", Fore.YELLOW)
                time.sleep(sleep_time)
        
        # ループが正常に完了することは基本的にないが、念のため
        return ""

    def _create_global_analysis_prompt(self, today, query, news_text):
        """世界情勢分析用プロンプト作成"""
        return f"""
Today's Date: {today}
Search Query: "{query}"

Please analyze the following news articles and assess their potential impact on the Chinese economy and stock market.

News Articles:
{news_text}

Instructions:
1. Focus only on news that could meaningfully impact Chinese stocks or economy
2. Output your analysis in JAPANESE using this format:

【クエリ「{query}」の分析結果】

**影響度: 高/中/低**

**ポジティブ要因:**
- yyyy/mm/dd: [記事タイトル] \n → 記事タイトル（日本語訳）とその影響

**ネガティブ要因:**
- yyyy/mm/dd: [記事タイトル] \n → 記事タイトル（日本語訳）とその影響

**注目すべき記事:**
- yyyy/mm/dd: [記事タイトル要約] \n → （日本語訳）] → 記事タイトル（日本語訳）と中国株への影響

**総合評価:**
[この検索結果全体の中国経済・株式市場への影響度合いと方向性]

Important Notes:
- Output everything in JAPANESE
- Focus on indirect impacts through trade, policy, global demand, etc.
- If no relevant impact is found, state "中国経済への直接的影響は限定的"
- Be specific about the transmission mechanism to Chinese markets
"""

    def _create_china_analysis_prompt(self, today, query, news_text):
        """中国情勢分析用プロンプト作成"""
        companies_text = ", ".join(self.target_companies)
        
        return f"""
Today's Date: {today}
Search Query: "{query}"
Target Companies: {companies_text}

Please analyze the following China-related news and assess their impact on Chinese stocks.

News Articles:
{news_text}

Instructions:
1. Focus on direct impacts to Chinese companies and economy
2. Output your analysis in JAPANESE using this format:

【クエリ「{query}」の分析結果】

**影響度: 高/中/低**

**株価上昇要因:**
- yyyy/mm/dd: [記事タイトル] \n → 記事タイトル（日本語訳）とその影響

**株価下落要因:**
- yyyy/mm/dd: [記事タイトル] \n → 記事タイトル（日本語訳）とその影響

**個別企業への影響:**
- [企業名]: [ニュース概要] \n → 記事タイトル（日本語訳）と影響: 上昇/下落/中立

**注目すべき記事:**
- yyyy/mm/dd: [記事タイトル] \n →  記事タイトル（日本語訳）と市場影響: [説明]

**総合評価:**
[この検索結果全体の中国株式市場への影響度合いと方向性]

Important Notes:
- Output everything in JAPANESE
- Consider policy changes, regulations, economic indicators
- Focus on our target companies when mentioned
- If no significant impact, state "市場への影響は限定的"
"""

    def search_and_analyze_realtime(self, queries, analysis_type="global", category_name=""):
        """検索と分析をリアルタイムで実行"""
        self.colored_print(f"\n{'='*60}", Fore.BLUE, Style.BRIGHT)
        self.colored_print(f" {datetime.now().strftime('%Y/%m/%d')} {category_name} - リアルタイム分析開始", Fore.BLUE, Style.BRIGHT)
        self.colored_print(f"{'='*60}", Fore.BLUE, Style.BRIGHT)
        
        analysis_results = []
        
        for i, query in enumerate(queries, 1):
            self.colored_print(f"\n[{i}/{len(queries)}] 🔄 処理中: \"{query}\"", Fore.CYAN, Style.BRIGHT)
            
            # 1. ニュース検索
            news_data = self.search_google_news_single(query, max_results=25)
            
            # 2. 即座にLLM分析
            if news_data:
                analysis_result = self.analyze_news_with_llm(news_data, query, analysis_type)
                if analysis_result:
                    analysis_results.append({
                        'query': query,
                        'analysis': analysis_result,
                        'news_count': len(news_data)
                    })
                    
                    # 分析結果を即座に表示
                    self.colored_print(f"\n📊 分析結果 (クエリ: {query})", Fore.GREEN, Style.BRIGHT)
                    print(analysis_result)
                    
            else:
                self.colored_print(f"⚠️  ニュースが取得できませんでした: \"{query}\"", Fore.YELLOW)
            
            # レート制限対策（最後のクエリ以外）
            if i < len(queries):
                wait_time = random.uniform(8.0, 12.0)
                self.colored_print(f"⏳ {wait_time:.1f}秒待機中...", Fore.YELLOW)
                time.sleep(wait_time)
        
        # カテゴリ全体の結果保存
        if analysis_type == "global":
            self.global_analysis_results.extend(analysis_results)
        else:
            self.china_analysis_results.extend(analysis_results)
        
        self.colored_print(f"\n✅ {category_name} 完了: {len(analysis_results)}件の分析結果", Fore.GREEN, Style.BRIGHT)
        return analysis_results

    def generate_comprehensive_summary(self):
        """全分析結果を統合した最終判断"""
        if not self.global_analysis_results and not self.china_analysis_results:
            self.colored_print("⚠️  統合できる分析結果がありません", Fore.YELLOW)
            return
        
        today = datetime.now().strftime("%Y/%m/%d")
        
        # 世界情勢分析結果の統合
        global_summary = "\n".join([
            f"【{result['query']}】\n{result['analysis']}\n" 
            for result in self.global_analysis_results
        ])
        
        # 中国情勢分析結果の統合
        china_summary = "\n".join([
            f"【{result['query']}】\n{result['analysis']}\n" 
            for result in self.china_analysis_results
        ])
        
        prompt = f"""
Today's Date: {today}

Please provide a comprehensive investment judgment by integrating all the following analysis results.

【Global Situation Analysis Results】
{global_summary}

【China Situation Analysis Results】
{china_summary}

Instructions:
Create a final comprehensive judgment in JAPANESE using this format:

【🎯 最終投資判断】
**総合判断: 強気/弱気/中立**
**確信度: 高/中/低**

【📊 判断根拠】
**世界情勢からの影響:**
- [世界経済が中国株に与える主要な影響要因]

**中国国内情勢:**
- [中国国内の重要なポジティブ・ネガティブ要因]

**個別企業要因:**
- [対象企業に関する重要な材料]

【💡 推奨アクション】
- [具体的な投資行動の提案]

【⚠️  主要リスク要因】
- [今後注意すべき重要なリスク]

【📈 セクター別見通し】
- [技術株、消費関連株、不動産関連株等の見通し]

Important Notes:
- Output everything in JAPANESE
- Balance both global and domestic factors
- Provide actionable insights
- Consider risk-reward balance
"""
        try:
            self.colored_print(f"\n{'='*60}", Fore.RED, Style.BRIGHT)
            self.colored_print("  🎯 最終統合分析実行中", Fore.RED, Style.BRIGHT)
            self.colored_print(f"{'='*60}", Fore.RED, Style.BRIGHT)
            
            # --- ▼▼▼ ここからが変更箇所 ▼▼▼ ---
            url = f"{self.base_url}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://realtime-news-analyzer.com", # 任意ヘッダー
                "X-Title": "Real-time News Analyzer Final Summary", # 任意ヘッダー
            }
            
            payload = {
                "model": "mistralai/mistral-small",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.2
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            
            response_data = response.json()
            final_result = response_data['choices'][0]['message']['content']
            # --- ▲▲▲ ここまでが変更箇所 ▲▲▲ ---
            
            self.colored_print(f"\n🎯 最終投資判断", Fore.RED, Style.BRIGHT)
            print(final_result)
            
            # 統計情報表示
            total_global = len(self.global_analysis_results)
            total_china = len(self.china_analysis_results)
            total_news = sum(r['news_count'] for r in self.global_analysis_results + self.china_analysis_results)
            
            self.colored_print(f"\n📊 分析統計", Fore.BLUE, Style.BRIGHT)
            self.colored_print(f"世界情勢クエリ: {total_global}件", Fore.WHITE)
            self.colored_print(f"中国情勢クエリ: {total_china}件", Fore.WHITE)
            self.colored_print(f"総記事数: {total_news}件", Fore.WHITE)
            
        except Exception as e:
            self.colored_print(f"❌ 最終分析エラー: {e}", Fore.RED)

    def run_realtime_analysis(self):
        """メイン実行プロセス"""
        self.colored_print("="*70, Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"    🚀{datetime.now().strftime('%Y/%m/%d')} リアルタイム ニュース分析システム", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print("="*70, Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"🕐 開始時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", Fore.WHITE)
        self.colored_print("📝 検索→分析→結果表示をリアルタイムで実行", Fore.WHITE)
        
        # 世界情勢関連クエリ
        global_queries = [
            "US economy news", 
            # "Federal Reserve interest rate",
            # "European economic outlook",
            # "global inflation trends",
            "US China trade relations",
            # "geopolitical risks markets"
        ]
        
        # 中国情勢関連クエリ  
        china_queries = [
            "China economy news",
            "Chinese stock market news",
            # "China property market",
            # "China tech regulation",
            # "Alibaba Tencent news",
            # "BYD Xiaomi news today"
        ]
        
        # 1. 世界情勢をリアルタイム分析
        self.search_and_analyze_realtime(
            global_queries, 
            analysis_type="global", 
            category_name="🌍 世界情勢"
        )
        
        # 2. 中国情勢をリアルタイム分析
        self.search_and_analyze_realtime(
            china_queries, 
            analysis_type="china", 
            category_name="🇨🇳 中国情勢"
        )
        
        # 3. 最終統合分析
        self.generate_comprehensive_summary()
        
        self.colored_print(f"\n{'='*70}", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"✅ 分析完了 - {datetime.now().strftime('%H:%M:%S')}", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"{'='*70}", Fore.MAGENTA, Style.BRIGHT)


def main():
    import os
    
    # APIキー設定
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print(f"{Fore.RED}❌ エラー: OpenRouter APIキーが設定されていません。")
        return
    
    # アナライザー実行
    analyzer = RealTimeNewsAnalyzer(api_key)
    analyzer.run_realtime_analysis()


if __name__ == "__main__":
    main()