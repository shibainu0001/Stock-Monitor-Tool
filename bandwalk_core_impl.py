import sys
import csv
import math
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 定数定義
BAND_WALK_DAYS = 6  # 固定値（実際は過去5日間を評価）
BB_PERIOD = 20  # ボリンジャーバンド期間
BB_STD = 2.0    # ボリンジャーバンド標準偏差
MA25_PERIOD = 25  # 移動平均期間

# ANSI色コード定義
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def colored_print(text, color=Colors.WHITE):
    """色付きprint"""
    print(f"{color}{text}{Colors.END}")

class DataRow:
    """データ行を表すクラス"""
    def __init__(self, date, nav, daily_change, total_assets):
        self.date = date
        self.nav = nav
        self.daily_change = daily_change
        self.total_assets = total_assets
        self.sma_20 = None
        self.std_20 = None
        self.bb_upper = None
        self.bb_lower = None
        self.ma25 = None

def parse_date(date_str):
    """日付文字列をdatetimeオブジェクトに変換"""
    try:
        # いくつかの日付フォーマットに対応
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unsupported date format: {date_str}")
    except:
        return None

def parse_number(value_str):
    """数値文字列を浮動小数点数に変換"""
    try:
        if value_str is None or value_str == '':
            return 0.0
        # カンマを除去
        cleaned = str(value_str).replace(',', '')
        return float(cleaned)
    except:
        return 0.0

def load_and_prepare_data(filename, fund_title):
    """CSVファイルを読み込んで前処理を行う"""
    try:
        data = []
        
        with open(filename, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)  # ヘッダー行をスキップ
            
            for row in csv_reader:
                if len(row) >= 4:
                    date = parse_date(row[0])
                    if date is not None:
                        nav = parse_number(row[1])
                        daily_change = parse_number(row[2])
                        total_assets = parse_number(row[3])
                        
                        data_row = DataRow(date, nav, daily_change, total_assets)
                        data.append(data_row)
        
        # 日付順にソート
        data.sort(key=lambda x: x.date)
        
        colored_print(f"=== {fund_title} ===", Colors.BOLD + Colors.MAGENTA)
        colored_print(f"データロード完了: {len(data)}日分のデータ", Colors.GREEN)
        
        if data:
            colored_print(f"データ期間: {data[0].date.strftime('%Y/%m/%d')} ～ {data[-1].date.strftime('%Y/%m/%d')}", Colors.BLUE)
        
        return data
        
    except Exception as e:
        colored_print(f"データロードエラー: {e}", Colors.RED)
        return None

def calculate_moving_average(data, period, start_idx):
    """移動平均を計算"""
    if start_idx < period - 1:
        return None
    
    sum_values = 0
    for i in range(period):
        sum_values += data[start_idx - i].nav
    
    return sum_values / period

def calculate_standard_deviation(data, period, start_idx, mean_value):
    """標準偏差を計算"""
    if start_idx < period - 1 or mean_value is None:
        return None
    
    sum_squares = 0
    for i in range(period):
        diff = data[start_idx - i].nav - mean_value
        sum_squares += diff * diff
    
    variance = sum_squares / period
    return math.sqrt(variance)

def calculate_bollinger_bands(data):
    """ボリンジャーバンドと移動平均を計算"""
    
    for i in range(len(data)):
        # 20日移動平均（中央線）
        data[i].sma_20 = calculate_moving_average(data, BB_PERIOD, i)
        
        # 20日標準偏差
        if data[i].sma_20 is not None:
            data[i].std_20 = calculate_standard_deviation(data, BB_PERIOD, i, data[i].sma_20)
        
        # ボリンジャーバンド上限・下限
        if data[i].sma_20 is not None and data[i].std_20 is not None:
            data[i].bb_upper = data[i].sma_20 + (BB_STD * data[i].std_20)
            data[i].bb_lower = data[i].sma_20 - (BB_STD * data[i].std_20)
        
        # 25日移動平均
        data[i].ma25 = calculate_moving_average(data, MA25_PERIOD, i)
    
    return data

def calculate_band_position(price, bb_upper, bb_lower):
    """バンド内での相対位置を計算（0=下限, 1=上限）"""
    if bb_upper != bb_lower:
        position = (price - bb_lower) / (bb_upper - bb_lower)
    else:
        position = 0.5
    return position

def check_band_walk(data, current_idx):
    """バンドウォーク判定を行う"""
    lookback = BAND_WALK_DAYS
    
    # 現在から過去5日分のデータが必要
    if current_idx < lookback - 1:
        return 'insufficient_data', '十分なデータがありません', False
    
    upper_walk_count = 0
    lower_walk_count = 0
    positions = []
    
    # 過去5日間をチェック
    for i in range(lookback):
        idx = current_idx - i
        
        check_price = data[idx].nav
        check_bb_upper = data[idx].bb_upper
        check_bb_lower = data[idx].bb_lower
        
        if check_bb_upper is None or check_bb_lower is None:
            return 'insufficient_data', '十分なデータがありません', False
        
        # バンド内位置を計算
        position = calculate_band_position(check_price, check_bb_upper, check_bb_lower)
        positions.append(position)
        
        # 上限付近（85%以上）かチェック
        if position >= 0.85:
            upper_walk_count += 1
        
        # 下限付近（15%以下）かチェック
        if position <= 0.15:
            lower_walk_count += 1
    
    # 現在の状態
    current_price = data[current_idx].nav
    current_bb_upper = data[current_idx].bb_upper
    current_bb_lower = data[current_idx].bb_lower
    current_ma25 = data[current_idx].ma25
    
    if current_ma25 is None:
        return 'insufficient_data', '十分なデータがありません', False
    
    current_position = calculate_band_position(current_price, current_bb_upper, current_bb_lower)
    current_above_ma = current_price > current_ma25
    current_below_ma = current_price < current_ma25
    
    avg_position = sum(positions) / len(positions)
    
    # 上昇バンドウォーク判定
    if upper_walk_count == lookback and avg_position >= 0.85 and current_above_ma:
        if current_position < 0.7:
            return 'sell', f'上昇バンドウォーク（{lookback-1}日継続）からの剥離', True
        else:
            return 'hold', f'上昇バンドウォーク継続中（{lookback-1}日継続）', True
    
    # 下降バンドウォーク判定
    if lower_walk_count == lookback and avg_position <= 0.15 and current_below_ma:
        if current_position > 0.3:
            return 'buy', f'下降バンドウォーク（{lookback-1}日継続）からの剥離', True
        else:
            return 'hold', f'下降バンドウォーク継続中（{lookback-1}日継続）', True
    
    return 'normal', '通常状態', False

def analyze_recent_data(data, fund_title, days=15):
    """過去N日の分析結果を表示"""
    colored_print(f"\n=== {fund_title} - 過去{days}日の分析結果 ===", Colors.BOLD + Colors.MAGENTA)
    colored_print("-" * 80, Colors.WHITE)
    
    # 最新のデータから過去N日分を取得
    start_idx = max(0, len(data) - days)
    recent_data = data[start_idx:]
    
    for i, row in enumerate(recent_data):
        original_idx = start_idx + i
        
        # バンドウォーク判定
        action, message, is_bandwalk = check_band_walk(data, original_idx)
        
        if row.bb_upper is None or row.bb_lower is None:
            continue
        
        # バンド内位置
        position = calculate_band_position(row.nav, row.bb_upper, row.bb_lower)
        
        # バンドとの価格差
        upper_diff = row.bb_upper - row.nav
        lower_diff = row.nav - row.bb_lower        
        
        # 状態表示
        status_color = "🔴" if action == "sell" else "🟢" if action == "buy" else "⚪"
        bandwalk_mark = "🚨" if is_bandwalk else ""
        
        # 日付表示（色付き）
        date_str = row.date.strftime('%Y/%m/%d')
        colored_print(f"{fund_title} {date_str} {status_color}{bandwalk_mark}", Colors.BOLD + Colors.CYAN)
        
        # 価格表示
        change_color = Colors.RED if row.daily_change < 0 else Colors.GREEN if row.daily_change > 0 else Colors.WHITE
        print(f"価格: {row.nav:,.0f}円 ", end="")
        colored_print(f"(前日比: {row.daily_change:+.0f}円)", change_color)
        
        # バンド位置表示（色分け）
        if position > 1.0:
            position_color = Colors.RED
            position_status = "⚠️ 上限突破!"
        elif position < 0.0:
            position_color = Colors.RED
            position_status = "⚠️ 下限突破!"
        elif position >= 0.85:
            position_color = Colors.YELLOW
            position_status = "⚠️ 上限付近"
        elif position <= 0.15:
            position_color = Colors.CYAN
            position_status = "⚠️ 下限付近"
        else:
            position_color = Colors.WHITE
            position_status = ""
        
        print("　バンド幅:", row.bb_upper - row.bb_lower)
        print(f"  バンド位置: ", end="")
        colored_print(f"{position:.3f} (0=下限, 1=上限) {position_status}", position_color)
        
        # バンドとの距離
        print(f"  上限との差: {upper_diff:+.0f}円, 下限との差: {lower_diff:+.0f}円")
        
        # 状態メッセージ
        if action == "sell":
            message_color = Colors.RED + Colors.BOLD
        elif action == "buy":
            message_color = Colors.GREEN + Colors.BOLD
        elif is_bandwalk:
            message_color = Colors.YELLOW + Colors.BOLD
        else:
            message_color = Colors.WHITE
        
        print(f"  状態: ", end="")
        colored_print(message, message_color)
        print()

def main():
    """メイン処理"""
    # 引数チェック
    if len(sys.argv) < 4:
        colored_print("使用方法: python script.py <id> <output_dir_base> <fund_title>", Colors.RED)
        colored_print("例: python script.py 123456 ./output 'サンプルファンド'", Colors.YELLOW)
        sys.exit(1)
    
    # データ読み込み
    id = sys.argv[1]
    output_dir_base = sys.argv[2]
    fund_title = sys.argv[3]

    filename = f"{id}_.csv"
    data = load_and_prepare_data(filename, fund_title)
    
    if data is None:
        return
    
    # ボリンジャーバンドの計算
    data = calculate_bollinger_bands(data)
    
    # 過去10日の分析
    analyze_recent_data(data, fund_title, days=10)

if __name__ == "__main__":
    main()