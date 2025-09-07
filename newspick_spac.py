import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timedelta
import re
from urllib.parse import quote
import json
from colorama import Fore, Style, init

# カラー出力の初期化
init(autoreset=True)

class IndexPredictionAnalyzer:
    def __init__(self, openrouter_api_key):
        self.openrouter_api_key = openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.target_indices = ["MSCI ACWI", "S&P500"]
        self.us_economy_results = []
        self.msci_acwi_results = []
        self.sp500_results = []
        
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

    def analyze_news_with_llm(self, news_data, query, analysis_type="us_economy"):
        """LLMを使用してニュースを分析（最大15回のリトライ機能付き）"""
        if not news_data:
            return ""

        today = datetime.now().strftime("%Y/%m/%d")
        news_text = "\n".join([
            f"Date: {item['date']}\nTitle: {item['title']}\nSource: {item['source']}\nSnippet: {item['snippet']}\n---"
            for item in news_data
        ])

        if analysis_type == "us_economy":
            prompt = self._create_us_economy_analysis_prompt(today, query, news_text)
        elif analysis_type == "msci_acwi":
            prompt = self._create_msci_acwi_analysis_prompt(today, query, news_text)
        elif analysis_type == "sp500":
            prompt = self._create_sp500_analysis_prompt(today, query, news_text)

        max_retries = 15
        for attempt in range(max_retries):
            try:
                self.colored_print(f"🤖 LLM分析開始 (試行 {attempt + 1}/{max_retries}, クエリ: {query})", Fore.MAGENTA)

                url = f"{self.base_url}/chat/completions"
                
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://index-prediction-analyzer.com",
                    "X-Title": "Index Prediction Analyzer",
                }
                
                payload = {
                    "model": "mistralai/mistral-small",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3500,
                    "temperature": 0.3
                }

                response = requests.post(url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                
                response_data = response.json()
                result = response_data['choices'][0]['message']['content']

                if len(result.strip()) <= 0:
                    raise ValueError(result)

                self.colored_print(f"✅ LLM分析完了 (クエリ: {query})", Fore.GREEN)
                return result

            except Exception as e:
                if attempt + 1 == max_retries:
                    self.colored_print(f"❌ LLM分析が{max_retries}回すべて失敗しました (クエリ: {query}): {e}", Fore.RED, Style.BRIGHT)
                    return ""
                
                backoff_time = (2 ** attempt) + random.uniform(0, 1)
                sleep_time = min(backoff_time, 60)

                self.colored_print(f"⚠️  LLM分析エラー (試行 {attempt + 1}/{max_retries}): {e}", Fore.YELLOW)
                self.colored_print(f"⏳ {sleep_time:.1f}秒後に再試行します...", Fore.YELLOW)
                time.sleep(sleep_time)
        
        return ""

    def _create_us_economy_analysis_prompt(self, today, query, news_text):
        """米国経済分析用プロンプト作成"""
        return f"""
Today's Date: {today}
Search Query: "{query}"

Please analyze the following US economic news articles and assess their potential impact on MSCI ACWI and S&P 500 indices.

News Articles:
{news_text}

Instructions:
1. Focus on economic indicators, Fed policy, inflation, employment, GDP, etc.
2. Output your analysis in JAPANESE using this format:

【クエリ「{query}」の米国経済分析】

**経済状況評価: 良好/普通/悪化**

**株式市場への上昇要因:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約と株価への影響

**株式市場への下落要因:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約と株価への影響

**Fed政策・金利関連:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約と市場への影響

**経済指標関連:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約と指標の意味

**MSCI ACWI への影響予測:**
[米国経済状況がMSCI ACWIに与える影響の分析]

**S&P 500 への影響予測:**
[米国経済状況がS&P 500に与える影響の分析]

**総合評価:**
[米国経済全体の現状評価と今後の見通し]

Important Notes:
- Output everything in JAPANESE
- Focus on macroeconomic factors that drive broad market indices
- Consider both domestic US factors and global implications
- If limited relevant news, state "関連する重要な経済ニュースは限定的"
"""

    def _create_msci_acwi_analysis_prompt(self, today, query, news_text):
        """MSCI ACWI分析用プロンプト作成"""
        return f"""
Today's Date: {today}
Search Query: "{query}"

Please analyze the following news related to MSCI ACWI and assess the price movement predictions and market outlook.

News Articles:
{news_text}

Instructions:
1. Focus on MSCI ACWI index movements, predictions, and related global market factors
2. Output your analysis in JAPANESE using this format:

【クエリ「{query}」のMSCI ACWI分析】

**値動き予測: 上昇/下落/横ばい**
**予測確信度: 高/中/低**

**上昇要因:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約とMSCI ACWIへの影響

**下落要因:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約とMSCI ACWIへの影響

**地域別影響:**
- 米国: [影響要因とMSCI ACWIへの寄与]
- 欧州: [影響要因とMSCI ACWIへの寄与]
- 新興国: [影響要因とMSCI ACWIへの寄与]
- その他: [影響要因とMSCI ACWIへの寄与]

**セクター別影響:**
- [主要セクターのMSCI ACWI構成比率への影響分析]

**専門家予測・アナリスト見解:**
- yyyy/mm/dd: [記事タイトル(原文)] \n → 専門家の予測内容と根拠の日本語要約

**技術的分析要因:**
- [チャート分析、サポート・レジスタンスレベル等の情報]

**今後1ヶ月の見通し:**
[短期的なMSCI ACWIの値動き予測と主要リスク要因]

**今後3ヶ月の見通し:**
[中期的なMSCI ACWIの値動き予測と構造的要因]

Important Notes:
- Output everything in JAPANESE
- Focus specifically on MSCI ACWI index performance and predictions
- Include global diversification aspects
- Consider both developed and emerging market factors
- If no direct MSCI ACWI news, analyze from global equity perspective
"""

    def _create_sp500_analysis_prompt(self, today, query, news_text):
        """S&P500分析用プロンプト作成"""
        return f"""
Today's Date: {today}
Search Query: "{query}"

Please analyze the following news related to S&P 500 and assess the price movement predictions and market outlook.

News Articles:
{news_text}

Instructions:
1. Focus on S&P 500 index movements, predictions, and US market factors
2. Output your analysis in JAPANESE using this format:

【クエリ「{query}」のS&P 500分析】

**値動き予測: 上昇/下落/横ばい**
**予測確信度: 高/中/低**

**上昇要因:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約とS&P 500への影響

**下落要因:**
- yyyy/mm/dd: [影響度] [記事タイトル(原文)] \n → 記事内容の日本語要約とS&P 500への影響

**主要企業・セクター影響:**
- テクノロジー: [AAPL, MSFT, GOOGL等への影響]
- ヘルスケア: [主要ヘルスケア企業への影響]
- 金融: [銀行・保険セクターへの影響]
- エネルギー: [石油・ガス企業への影響]
- その他重要セクター: [影響のある業種]

**企業決算・業績関連:**
- yyyy/mm/dd: [記事タイトル(原文)] \n → 主要企業の決算がS&P 500に与える影響

**専門家予測・アナリスト見解:**
- yyyy/mm/dd: [記事タイトル(原文)] \n → 専門家の予測内容と目標値の日本語要約

**技術的分析要因:**
- [チャート分析、移動平均線、サポート・レジスタンスレベル等]

**マクロ経済要因:**
- [Fed政策、雇用統計、インフレ指標等のS&P 500への影響]

**今後1ヶ月の見通し:**
[短期的なS&P 500の値動き予測と主要リスク要因]

**今後3ヶ月の見通し:**
[中期的なS&P 500の値動き予測と構造的要因]

**目標価格レンジ:**
[アナリストによる目標価格や予想レンジ]

Important Notes:
- Output everything in JAPANESE  
- Focus specifically on S&P 500 index performance and predictions
- Include major component stocks impact
- Consider both fundamental and technical factors
- Provide specific price targets when available
"""

    def search_and_analyze_realtime(self, queries, analysis_type, category_name=""):
        """検索と分析をリアルタイムで実行"""
        self.colored_print(f"\n{'='*50}", Fore.BLUE, Style.BRIGHT)
        self.colored_print(f"{datetime.now().strftime('%Y/%m/%d')} {category_name} - リアルタイム分析開始", Fore.BLUE, Style.BRIGHT)
        self.colored_print(f"{'='*50}", Fore.BLUE, Style.BRIGHT)
        
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
        
        # 結果保存
        if analysis_type == "us_economy":
            self.us_economy_results.extend(analysis_results)
        elif analysis_type == "msci_acwi":
            self.msci_acwi_results.extend(analysis_results)
        elif analysis_type == "sp500":
            self.sp500_results.extend(analysis_results)
        
        self.colored_print(f"\n✅ {category_name} 完了: {len(analysis_results)}件の分析結果", Fore.GREEN, Style.BRIGHT)
        return analysis_results

    def generate_comprehensive_summary(self):
        """全分析結果を統合した最終判断"""
        if not any([self.us_economy_results, self.msci_acwi_results, self.sp500_results]):
            self.colored_print("⚠️  統合できる分析結果がありません", Fore.YELLOW)
            return
        
        today = datetime.now().strftime("%Y/%m/%d")
        
        # 各分析結果の統合
        us_economy_summary = "\n".join([
            f"【{result['query']}】\n{result['analysis']}\n" 
            for result in self.us_economy_results
        ])
        
        msci_acwi_summary = "\n".join([
            f"【{result['query']}】\n{result['analysis']}\n" 
            for result in self.msci_acwi_results
        ])
        
        sp500_summary = "\n".join([
            f"【{result['query']}】\n{result['analysis']}\n" 
            for result in self.sp500_results
        ])
        
        prompt = f"""
Today's Date: {today}

Please provide comprehensive investment predictions for MSCI ACWI and S&P 500 by integrating all the following analysis results.

【US Economy Analysis Results】
{us_economy_summary}

【MSCI ACWI Analysis Results】
{msci_acwi_summary}

【S&P 500 Analysis Results】
{sp500_summary}

Instructions:
Create a final comprehensive prediction in JAPANESE using this format:

【🎯 最終投資予測】

【📈 MSCI ACWI 予測】
**値動き予測: 上昇/下落/横ばい**
**確信度: 高/中/低**
**予想変動率: ±X%**
**根拠:**
- [主要な上昇・下落要因]

【📊 S&P 500 予測】  
**値動き予測: 上昇/下落/横ばい**
**確信度: 高/中/低**
**予想変動率: ±X%**
**根拠:**
- [主要な上昇・下落要因]

【🌍 マクロ環境分析】
**米国経済状況:**
- [現在の経済状況とインデックスへの影響]

**金融政策影響:**
- [Fed政策がインデックスに与える影響]

**グローバル要因:**
- [国際情勢のインデックスへの影響]

【💡 投資戦略提案】
**MSCI ACWI:**
- [推奨投資アクションと理由]

**S&P 500:**
- [推奨投資アクションと理由]

【📅 時間軸別見通し】
**1週間以内:**
- MSCI ACWI: [短期予測]
- S&P 500: [短期予測]

**1ヶ月以内:**
- MSCI ACWI: [中期予測]  
- S&P 500: [中期予測]

**3ヶ月以内:**
- MSCI ACWI: [長期予測]
- S&P 500: [長期予測]

【⚠️  主要リスク要因】
- [注意すべき下落リスク]

【🚀 主要上昇カタリスト】  
- [期待できる上昇要因]

【📋 まとめ】
[両インデックスの総合的な投資判断]

Important Notes:
- Output everything in JAPANESE
- Provide specific percentage predictions when possible
- Balance both indices' outlooks
- Consider correlation and divergence factors
- Include actionable investment advice
"""
        
        try:
            self.colored_print(f"\n{'='*60}", Fore.RED, Style.BRIGHT)
            self.colored_print("  🎯 最終統合予測実行中", Fore.RED, Style.BRIGHT)
            self.colored_print(f"{'='*60}", Fore.RED, Style.BRIGHT)
            
            url = f"{self.base_url}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://index-prediction-analyzer.com",
                "X-Title": "Index Prediction Final Summary",
            }
            
            payload = {
                "model": "mistralai/mistral-small",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2500,
                "temperature": 0.2
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            
            response_data = response.json()
            final_result = response_data['choices'][0]['message']['content']
            
            self.colored_print(f"\n🎯 最終投資予測", Fore.RED, Style.BRIGHT)
            print(final_result)
            
            # 統計情報表示
            total_us = len(self.us_economy_results)
            total_acwi = len(self.msci_acwi_results)
            total_sp500 = len(self.sp500_results)
            total_news = sum(r['news_count'] for r in self.us_economy_results + self.msci_acwi_results + self.sp500_results)
            
            self.colored_print(f"\n📊 分析統計", Fore.BLUE, Style.BRIGHT)
            self.colored_print(f"米国経済クエリ: {total_us}件", Fore.WHITE)
            self.colored_print(f"MSCI ACWIクエリ: {total_acwi}件", Fore.WHITE)
            self.colored_print(f"S&P 500クエリ: {total_sp500}件", Fore.WHITE)
            self.colored_print(f"総記事数: {total_news}件", Fore.WHITE)
            
        except Exception as e:
            self.colored_print(f"❌ 最終分析エラー: {e}", Fore.RED)

    def run_index_prediction_analysis(self):
        """メイン実行プロセス"""
        self.colored_print("="*60, Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"🚀 {datetime.now().strftime('%Y/%m/%d')} MSCI ACWI & S&P500 値動き予測システム", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print("="*60, Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"🕐 開始時刻: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", Fore.WHITE)
        self.colored_print("📝 米国経済→各インデックス分析→総合予測の順で実行", Fore.WHITE)
        
        # 1. 米国経済状況関連クエリ
        us_economy_queries = [
            "US economy news",
            "Federal Reserve interest rate decision", 
            # "US inflation data CPI",
            "US employment jobs report",
            # "US GDP economic growth"
        ]
        
        # 2. MSCI ACWI関連クエリ
        msci_acwi_queries = [
            "MSCI ACWI",
            "MSCI ACWI price target forecast",
            # "MSCI ACWI performance outlook",
            # "global equity market forecast",
            # "MSCI world index analysis"
        ]
        
        # 3. S&P 500関連クエリ
        sp500_queries = [
            "S&P 500",
            "S&P 500 price target forecast",
            # "S&P 500 price target 2025",
            # "S&P 500 technical analysis",
            # "SPX index outlook forecast",
            # "S&P 500 analyst predictions"
        ]
        
        # 1. 米国経済状況をリアルタイム分析
        self.search_and_analyze_realtime(
            us_economy_queries, 
            analysis_type="us_economy", 
            category_name="🇺🇸 米国経済状況"
        )
        
        # 分析間の待機時間
        self.colored_print(f"\n⏳ セッション切替のため5秒待機中...", Fore.YELLOW)
        time.sleep(5)
        
        # 2. MSCI ACWIをリアルタイム分析
        self.search_and_analyze_realtime(
            msci_acwi_queries, 
            analysis_type="msci_acwi", 
            category_name="🌍 MSCI ACWI"
        )
        
        # 分析間の待機時間
        self.colored_print(f"\n⏳ セッション切替のため5秒待機中...", Fore.YELLOW)
        time.sleep(5)
        
        # 3. S&P 500をリアルタイム分析
        self.search_and_analyze_realtime(
            sp500_queries, 
            analysis_type="sp500", 
            category_name="📈 S&P 500"
        )
        
        # 4. 最終統合予測
        self.generate_comprehensive_summary()
        
        self.colored_print(f"\n{'='*60}", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"✅ 予測分析完了 - {datetime.now().strftime('%H:%M:%S')}", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print(f"{'='*60}", Fore.MAGENTA, Style.BRIGHT)


def main():
    import os
    
    # APIキー設定
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print(f"{Fore.RED}❌ エラー: OpenRouter APIキーが設定されていません。")
        print(f"{Fore.YELLOW}環境変数 'OPENROUTER_API_KEY' を設定してください。")
        return
    
    # アナライザー実行
    analyzer = IndexPredictionAnalyzer(api_key)
    analyzer.run_index_prediction_analysis()


if __name__ == "__main__":
    main()