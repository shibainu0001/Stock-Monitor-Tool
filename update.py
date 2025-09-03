import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import re
import os
import sys

def load_existing_data(csv_file):
    """
    既存のCSVファイルからデータを読み込む
    
    Args:
        csv_file (str): CSVファイルのパス
        
    Returns:
        dict: 日付をキーとした既存データの辞書
        list: 全てのデータ行のリスト
    """
    existing_dates = set()
    existing_data = []
    
    if os.path.exists(csv_file):
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # ヘッダーをスキップ
                
                for row in reader:
                    if len(row) >= 4:
                        date_str = row[0]
                        existing_dates.add(date_str)
                        existing_data.append(row)
                        
            print(f"既存データを読み込みました: {len(existing_data)}件")
        except Exception as e:
            print(f"既存ファイル読み込みエラー: {e}")
    else:
        print("新しいCSVファイルを作成します")
    
    return existing_dates, existing_data

def scrape_fund_data(fund_id):
    """
    Yahoo Finance Japanから投資信託のデータを取得し、既存CSVに追加する
    
    Args:
        fund_id (str): 投資信託のID（例: "04315213"）
    """
    
    # URLとファイル名を生成
    url = f"https://finance.yahoo.co.jp/quote/{fund_id}/history"
    csv_file = f"{fund_id}_.csv"
    
    print(f"投資信託ID: {fund_id}")
    print(f"URL: {url}")
    print(f"CSVファイル: {csv_file}")
    
    # 既存データを読み込み
    existing_dates, existing_data = load_existing_data(csv_file)
    
    # HTTPヘッダーを設定
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    try:
        # ページを取得
        print("ページを取得中...")
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"エラー: HTTPステータス {response.status_code}")
            return
        
        # BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # テーブルを探す
        table = None
        selectors = [
            'table',
            '.historyTable',
            '#historicalDataTable',
            '[data-test="historical-prices"]',
            'table[class*="history"]',
            'table[class*="data"]'
        ]
        
        for selector in selectors:
            table = soup.select_one(selector)
            if table:
                print(f"テーブルが見つかりました: {selector}")
                break
        
        if not table:
            # より広範囲に探す
            tables = soup.find_all('table')
            if tables:
                table = tables[0]
                print(f"最初のテーブルを使用: {len(tables)}個のテーブルが見つかりました")
            else:
                print("テーブル要素が見つかりません")
                return
        
        # 新しいデータを抽出
        new_data_rows = []
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                date_text = cell_texts[0]
                
                # 日付の形式を確認
                if re.search(r'\d{4}年\d{1,2}月\d{1,2}日', date_text):
                    try:
                        # 日付を変換
                        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
                        if date_match:
                            year, month, day = date_match.groups()
                            formatted_date = f"{year}/{month:0>2}/{day:0>2}"
                            
                            # 既存データに存在するかチェック
                            if formatted_date in existing_dates:
                                print(f"スキップ（既存）: {formatted_date}")
                                continue
                            
                            # 数値データをクリーンアップ
                            base_price = cell_texts[1].replace(',', '').replace('+', '')
                            daily_change = cell_texts[2].replace(',', '')
                            # +記号の処理（前日比）
                            if daily_change.startswith('+'):
                                daily_change = daily_change[1:]
                            net_assets = cell_texts[3].replace(',', '').replace('+', '')
                            
                            new_data_rows.append([formatted_date, base_price, daily_change, net_assets])
                            print(f"新規データ: {formatted_date}")
                            
                    except (ValueError, IndexError) as e:
                        print(f"データ解析エラー: {cell_texts} - {e}")
                        continue
        
        print(f"新規データ: {len(new_data_rows)}件")
        
        if new_data_rows:
            # 既存データと新規データをマージ
            all_data = existing_data + new_data_rows
            
            # 日付で昇順にソート
            all_data.sort(key=lambda x: datetime.strptime(x[0], '%Y/%m/%d'))
            
            # CSVファイルに保存
            with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # ヘッダーを書き込み
                writer.writerow(['年月日', '基準価額（円）', '前日比（円）', '純資産総額（百万円）'])
                
                # データを書き込み
                for row in all_data:
                    writer.writerow(row)
            
            print(f"CSVファイルを更新しました: {csv_file}")
            print(f"総データ数: {len(all_data)}件")
            
            # 新規追加されたデータを表示
            print(f"\n新規追加データ ({len(new_data_rows)}件):")
            for row in sorted(new_data_rows, key=lambda x: datetime.strptime(x[0], '%Y/%m/%d')):
                print(f'"{row[0]}","{row[1]}","{row[2]}","{row[3]}"')
        else:
            print("新規データはありませんでした")
            
    except requests.RequestException as e:
        print(f"リクエストエラー: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")

def scrape_multiple_funds(fund_ids):
    """
    複数の投資信託データを一度に取得する
    
    Args:
        fund_ids (list): 投資信託IDのリスト
    """
    for fund_id in fund_ids:
        print(f"\n{'='*50}")
        print(f"投資信託 {fund_id} を処理中...")
        print('='*50)
        scrape_fund_data(fund_id)
        print(f"投資信託 {fund_id} の処理完了")

def show_csv_summary(fund_id):
    """
    CSVファイルの要約を表示する
    
    Args:
        fund_id (str): 投資信託のID
    """
    csv_file = f"{fund_id}_.csv"
    
    if not os.path.exists(csv_file):
        print(f"ファイルが見つかりません: {csv_file}")
        return
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            data = list(reader)
        
        if not data:
            print("データがありません")
            return
            
        print(f"\n=== {csv_file} の要約 ===")
        print(f"総データ数: {len(data)}件")
        print(f"期間: {data[0][0]} ～ {data[-1][0]}")
        
        print("\n最初の5件:")
        for row in data[:5]:
            print(f'"{row[0]}","{row[1]}","{row[2]}","{row[3]}"')
            
        print("\n最新の5件:")
        for row in data[-5:]:
            print(f'"{row[0]}","{row[1]}","{row[2]}","{row[3]}"')
            
    except Exception as e:
        # print(f"ファイル読み込みエラー: {e}")
        pass

# 使用例
if __name__ == "__main__":
    # 投資信託ID
    fund_id = sys.argv[1]
    
    # データをスクレイピングしてCSVを更新
    scrape_fund_data(fund_id)
    
    # 結果の要約を表示
    show_csv_summary(fund_id)
    
    # 複数の投資信託を処理する場合の例
    # fund_ids = ["04315213", "04315214", "04315215"]
    # scrape_multiple_funds(fund_ids)