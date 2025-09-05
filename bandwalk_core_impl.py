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
MACD_FAST = 12  # MACD短期EMA期間
MACD_SLOW = 26  # MACD長期EMA期間
MACD_SIGNAL = 9  # MACDシグナル期間

# MACDシグナル設定（引数で変更可能）
UPPER_THRESHOLD = 0.5  # 上限閾値
LOWER_THRESHOLD = -0.5  # 下限閾値
UPPER_CROSS_RATE = 0.7  # 上限クロス率（70%）
LOWER_CROSS_RATE = 0.7  # 下限クロス率（70%）

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

class MacdSignalState:
    """MACDシグナル状態管理クラス"""
    def __init__(self):
        self.reset()
    
    def reset(self):
        """状態をリセット"""
        self.max_histogram = None
        self.min_histogram = None
        self.has_declined = False  # 下降を確認したフラグ
        self.has_inclined = False  # 上昇を確認したフラグ
        self.sell_signal = False
        self.buy_signal = False
        self.last_histogram = None

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
        self.ema_fast = None  # 12日EMA
        self.ema_slow = None  # 26日EMA
        self.macd = None      # MACD線
        self.macd_signal = None  # シグナル線
        self.macd_histogram = None  # ヒストグラム
        # MACDシグナル関連
        self.macd_sell_signal = False
        self.macd_buy_signal = False
        self.signal_reason = ""

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

def calculate_ema(data, period, start_idx):
    """指数移動平均（EMA）を計算"""
    if start_idx < period - 1:
        return None
    
    # 最初のEMAはSMAで初期化
    if start_idx == period - 1:
        sum_values = 0
        for i in range(period):
            sum_values += data[start_idx - i].nav
        return sum_values / period
    
    # EMA計算
    alpha = 2.0 / (period + 1)
    prev_ema = data[start_idx - 1].ema_fast if period == MACD_FAST else data[start_idx - 1].ema_slow
    if prev_ema is None:
        return None
    
    return alpha * data[start_idx].nav + (1 - alpha) * prev_ema

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

def calculate_macd_signal_ema(data, start_idx):
    """MACDシグナル線のEMAを計算"""
    if start_idx < MACD_SIGNAL - 1:
        return None
    
    # MACDが計算されていない場合はNone
    if data[start_idx].macd is None:
        return None
    
    # 最初のシグナルEMAはSMAで初期化
    if start_idx == MACD_SIGNAL - 1 or data[start_idx - 1].macd_signal is None:
        # 過去MACD_SIGNAL日分のMACDの平均
        sum_macd = 0
        valid_count = 0
        for i in range(MACD_SIGNAL):
            if start_idx - i >= 0 and data[start_idx - i].macd is not None:
                sum_macd += data[start_idx - i].macd
                valid_count += 1
        
        if valid_count == 0:
            return None
        return sum_macd / valid_count
    
    # シグナル線EMA計算
    alpha = 2.0 / (MACD_SIGNAL + 1)
    prev_signal = data[start_idx - 1].macd_signal
    if prev_signal is None:
        return None
    
    return alpha * data[start_idx].macd + (1 - alpha) * prev_signal

def detect_zero_cross(current_histogram, previous_histogram):
    """ゼロクロスを検出"""
    if current_histogram is None or previous_histogram is None:
        return False
    
    # 前回と今回で符号が変わった場合はゼロクロス
    return (current_histogram > 0 and previous_histogram <= 0) or \
           (current_histogram < 0 and previous_histogram >= 0)

def update_macd_signals(data, signal_state, current_idx):
    """MACDシグナルを更新"""
    if current_idx == 0:
        return
    
    current_row = data[current_idx]
    prev_row = data[current_idx - 1]
    
    current_histogram = current_row.macd_histogram
    prev_histogram = prev_row.macd_histogram
    
    if current_histogram is None:
        return
    
    # ゼロクロスチェック
    if detect_zero_cross(current_histogram, prev_histogram):
        signal_state.reset()
        signal_state.last_histogram = current_histogram
        # ゼロクロス情報を記録
        if current_histogram > 0:
            current_row.signal_reason = "MACD売買シグナル: なし - ゼロクロス上抜け"
        else:
            current_row.signal_reason = "MACD売買シグナル: なし - ゼロクロス下抜け"
        return
    
    # 最大値・最小値を更新
    if signal_state.max_histogram is None or current_histogram > signal_state.max_histogram:
        signal_state.max_histogram = current_histogram
    
    if signal_state.min_histogram is None or current_histogram < signal_state.min_histogram:
        signal_state.min_histogram = current_histogram
    
    # 下降・上昇フラグの更新
    if signal_state.last_histogram is not None:
        if current_histogram < signal_state.last_histogram:
            signal_state.has_declined = True
        if current_histogram > signal_state.last_histogram:
            signal_state.has_inclined = True
    
    # 売りシグナル判定
    if (not signal_state.sell_signal and 
        signal_state.has_declined and 
        signal_state.max_histogram is not None and
        signal_state.max_histogram > UPPER_THRESHOLD):
        
        cross_level = signal_state.max_histogram * UPPER_CROSS_RATE
        if current_histogram < cross_level:
            signal_state.sell_signal = True
            current_row.macd_sell_signal = True
            current_row.signal_reason = f"MACD売りシグナル: 最大値{signal_state.max_histogram:.3f}の{UPPER_CROSS_RATE*100:.0f}%({cross_level:.3f})を下抜け"
    
    # 買いシグナル判定
    if (not signal_state.buy_signal and 
        signal_state.has_inclined and 
        signal_state.min_histogram is not None and
        signal_state.min_histogram < LOWER_THRESHOLD):
        
        cross_level = signal_state.min_histogram * LOWER_CROSS_RATE
        if current_histogram > cross_level:
            signal_state.buy_signal = True
            current_row.macd_buy_signal = True
            current_row.signal_reason = f"MACD買いシグナル: 最小値{signal_state.min_histogram:.3f}の{LOWER_CROSS_RATE*100:.0f}%({cross_level:.3f})を上抜け"
    
    # シグナル継続中の場合
    if signal_state.sell_signal and not current_row.macd_sell_signal:
        current_row.macd_sell_signal = True
        current_row.signal_reason = "MACD売りシグナル継続中"
    
    if signal_state.buy_signal and not current_row.macd_buy_signal:
        current_row.macd_buy_signal = True
        current_row.signal_reason = "MACD買いシグナル継続中"
    
    # シグナルが出ていない場合の基本情報を設定
    if not current_row.signal_reason:
        if signal_state.max_histogram is not None and signal_state.min_histogram is not None:
            if current_histogram > 0:
                current_row.signal_reason = f"MACD売買シグナル: なし - プラス圏内 (最大値: {signal_state.max_histogram:.3f}, 現在値: {current_histogram:.3f})"
            else:
                current_row.signal_reason = f"MACD売買シグナル: なし - マイナス圏内 (最小値: {signal_state.min_histogram:.3f}, 現在値: {current_histogram:.3f})"
    
    signal_state.last_histogram = current_histogram

def calculate_indicators(data):
    """ボリンジャーバンド、移動平均、MACDを計算"""
    signal_state = MacdSignalState()
    
    for i in range(len(data)):
        # EMA計算
        data[i].ema_fast = calculate_ema(data, MACD_FAST, i)
        data[i].ema_slow = calculate_ema(data, MACD_SLOW, i)
        
        # MACD計算
        if data[i].ema_fast is not None and data[i].ema_slow is not None:
            data[i].macd = data[i].ema_fast - data[i].ema_slow
        
        # MACDシグナル線計算
        data[i].macd_signal = calculate_macd_signal_ema(data, i)
        
        # MACDヒストグラム計算
        if data[i].macd is not None and data[i].macd_signal is not None:
            data[i].macd_histogram = data[i].macd - data[i].macd_signal
        
        # MACDシグナル判定
        update_macd_signals(data, signal_state, i)
        
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

def get_macd_color(value):
    """MACD値に応じて色を返す"""
    if value is None:
        return Colors.WHITE
    elif value > 0:
        return Colors.GREEN
    else:
        return Colors.RED

def analyze_recent_data(data, fund_title, days=15):
    """過去N日の分析結果を表示"""
    colored_print(f"\n=== {fund_title} - 過去{days}日の分析結果 ===", Colors.BOLD + Colors.MAGENTA)
    colored_print(f"MACD設定: 上限閾値={UPPER_THRESHOLD}, 下限閾値={LOWER_THRESHOLD}, 上限クロス率={UPPER_CROSS_RATE*100:.0f}%, 下限クロス率={LOWER_CROSS_RATE*100:.0f}%", Colors.BLUE)
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
        
        # MACDシグナル表示
        macd_signal_mark = ""
        if row.macd_sell_signal:
            macd_signal_mark = "📉"
        elif row.macd_buy_signal:
            macd_signal_mark = "📈"
        
        # 日付表示（色付き）
        date_str = row.date.strftime('%Y/%m/%d')
        colored_print(f"{fund_title} {date_str} {status_color}{bandwalk_mark}{macd_signal_mark}", Colors.BOLD + Colors.CYAN)
        
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
        
        # MACD表示（色分け）
        if row.macd is not None and row.macd_signal is not None:
            macd_color = get_macd_color(row.macd)
            signal_color = get_macd_color(row.macd_signal)
            histogram_color = get_macd_color(row.macd_histogram)
            
            print(f"  MACD: ", end="")
            colored_print(f"{row.macd:+.2f}", macd_color)
            print(f"  シグナル: ", end="")
            colored_print(f"{row.macd_signal:+.2f}", signal_color)
            print(f"  ヒストグラム: ", end="")
            colored_print(f"{row.macd_histogram:+.2f}", histogram_color)
        
        # MACDシグナル表示（常に表示）
        if row.signal_reason:
            signal_color = Colors.RED + Colors.BOLD if row.macd_sell_signal else Colors.GREEN + Colors.BOLD if row.macd_buy_signal else Colors.CYAN
            print(f"  📊 ", end="")
            colored_print(row.signal_reason, signal_color)
        
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


def draw_recent_chart(data, fund_title, days=7):
    """過去N日の株価とボリンジャーバンド、MACDヒストグラムをASCIIチャートで表示"""
    try:
        import asciichartpy
    except ImportError:
        colored_print("asciichartpyがインストールされていません。", Colors.RED)
        colored_print("pip install asciichartpy でインストールしてください。", Colors.YELLOW)
        return
    
    # 最新のデータから過去N日分を取得
    start_idx = max(0, len(data) - days)
    recent_data = data[start_idx:]
    
    # 有効なデータのみを抽出
    valid_data = [row for row in recent_data if row.bb_upper is not None and row.bb_lower is not None]
    
    if len(valid_data) < 2:
        colored_print("グラフ表示に必要なデータが不足しています。", Colors.RED)
        return
    
    # データ準備
    dates = [row.date.strftime('%m/%d') for row in valid_data]
    prices = [row.nav for row in valid_data]
    bb_upper = [row.bb_upper for row in valid_data]
    bb_lower = [row.bb_lower for row in valid_data]
    sma_20 = [row.sma_20 for row in valid_data]
    macd_histogram = [row.macd_histogram if row.macd_histogram is not None else 0 for row in valid_data]
    
    # グラフ表示
    colored_print(f"\n=== {fund_title} - 過去{len(valid_data)}日のチャート ===", Colors.BOLD + Colors.MAGENTA)
    colored_print("-" * 60, Colors.WHITE)
    
    # 価格範囲の調整（見やすくするため）
    min_price = min(min(bb_lower), min(prices))
    max_price = max(max(bb_upper), max(prices))
    price_range = max_price - min_price
    margin = price_range * 0.05  # 5%のマージン
    
    # ===== 株価・ボリンジャーバンドグラフ =====
    chart_config = {
        'height': 15,
        'format': lambda x, i: f'{int(x):,}',
        'min': min_price - margin,
        'max': max_price + margin
    }
    
    # 複数系列を同一グラフに表示
    colored_print("📈 株価 & ボリンジャーバンド", Colors.BOLD + Colors.GREEN)
    
    # 複数の系列をまとめて表示
    series = [sma_20, prices, bb_upper, bb_lower]
    colors = [
        asciichartpy.yellow,   # 中央線 (黄)
        asciichartpy.green,    # 株価 (緑)
        asciichartpy.red,      # ボリンジャーバンド上限 (赤)
        asciichartpy.cyan      # ボリンジャーバンド下限 (青)
    ]
    
    # カラー設定を含む設定
    chart_config_multi = {
        'height': 20,
        'min': min_price - margin,
        'max': max_price + margin,
        'colors': colors
    }
    
    print(asciichartpy.plot(series, chart_config_multi))
    
    # 凡例表示
    colored_print("    凡例:", Colors.BOLD + Colors.WHITE)
    colored_print("    🔴 ボリンジャーバンド上限 (+2σ)", Colors.RED)
    colored_print("    🟢 株価 (NAV)", Colors.GREEN)
    colored_print("    🟡 中央線 (20日SMA)", Colors.YELLOW)
    colored_print("    🔵 ボリンジャーバンド下限 (-2σ)", Colors.BLUE)
    
    # 日付ラベル表示
    date_line = "    "  # インデント調整
    for i, date in enumerate(dates):
        if i == 0:
            date_line += date
        else:
            # 適切な間隔で日付を配置
            spaces = " " * max(1, 8 - len(date))  # 調整値
            date_line += spaces + date
    colored_print(date_line.replace("   ", " "), Colors.CYAN)
    
    print()
    
    # ===== MACDヒストグラムグラフ =====
    colored_print("📊 MACDヒストグラム", Colors.BOLD + Colors.MAGENTA)
    
    # MACDヒストグラムの範囲設定（0を中央にする）
    hist_abs_max = max(abs(min(macd_histogram)), abs(max(macd_histogram)))
    hist_margin = hist_abs_max * 0.1
    
    # ゼロを中央にするため、上下対称の範囲を設定
    chart_min = -(hist_abs_max + hist_margin)
    chart_max = hist_abs_max + hist_margin
    
    # MACDヒストグラム用の設定（0ライン + ヒストグラム）
    hist_config = {
        'height': 12,
        'min': chart_min,
        'max': chart_max,
        'colors': [
            asciichartpy.white,    # ゼロライン (白)
            asciichartpy.cyan      # ヒストグラム (シアン)
        ]
    }
    
    # ゼロラインとヒストグラムを表示
    zero_line = [0] * len(macd_histogram)
    hist_series = [zero_line, macd_histogram]
    
    print(asciichartpy.plot(hist_series, hist_config))
    
    # MACDヒストグラム凡例
    # colored_print("    凡例:", Colors.BOLD + Colors.WHITE)
    # colored_print("    ⚪ ゼロライン", Colors.WHITE)
    # colored_print("    🔵 MACDヒストグラム (正: 買い優勢, 負: 売り優勢)", Colors.CYAN)
    
    # MACDヒストグラム用の日付ラベル表示
    colored_print(date_line.replace("   ", " "), Colors.CYAN)
    
    print()
    
    # 数値サマリー
    # colored_print("=== 数値サマリー ===", Colors.BOLD + Colors.WHITE)
    latest = valid_data[-1]
    # colored_print(f"最新価格: {latest.nav:,.0f}円", Colors.GREEN)
    # colored_print(f"上限: {latest.bb_upper:,.0f}円 (差: {latest.bb_upper - latest.nav:+.0f}円)", Colors.RED)
    # colored_print(f"中央: {latest.sma_20:,.0f}円 (差: {latest.sma_20 - latest.nav:+.0f}円)", Colors.YELLOW)
    # colored_print(f"下限: {latest.bb_lower:,.0f}円 (差: {latest.nav - latest.bb_lower:+.0f}円)", Colors.BLUE)
    
    # バンド内位置
    position = calculate_band_position(latest.nav, latest.bb_upper, latest.bb_lower)
    # colored_print(f"バンド内位置: {position:.1%} (0%=下限, 100%=上限)", Colors.CYAN)
    
    # MACDサマリー
    # if latest.macd_histogram is not None:
        # hist_color = Colors.GREEN if latest.macd_histogram > 0 else Colors.RED if latest.macd_histogram < 0 else Colors.WHITE
        # print(f"MACDヒストグラム: ", end="")
        # colored_print(f"{latest.macd_histogram:+.3f}", hist_color)
    
    print()

def main():
    """メイン処理"""
    # 引数チェック
    if len(sys.argv) < 4:
        colored_print("使用方法: python script.py <id> <output_dir_base> <fund_title> [upper_threshold] [lower_threshold] [upper_cross_rate] [lower_cross_rate]", Colors.RED)
        colored_print("例: python script.py 123456 ./output 'サンプルファンド' 0.5 -0.5 0.7 0.6", Colors.YELLOW)
        sys.exit(1)
    
    # パラメータ設定
    global UPPER_THRESHOLD, LOWER_THRESHOLD, UPPER_CROSS_RATE, LOWER_CROSS_RATE
    
    if len(sys.argv) >= 5:
        UPPER_THRESHOLD = float(sys.argv[4])
    if len(sys.argv) >= 6:
        LOWER_THRESHOLD = float(sys.argv[5])
    if len(sys.argv) >= 7:
        UPPER_CROSS_RATE = float(sys.argv[6])
    if len(sys.argv) >= 8:
        LOWER_CROSS_RATE = float(sys.argv[7])
    
    # データ読み込み
    id = sys.argv[1]
    output_dir_base = sys.argv[2]
    fund_title = sys.argv[3]

    filename = f"{id}_.csv"
    data = load_and_prepare_data(filename, fund_title)
    
    if data is None:
        return
    
    # ボリンジャーバンドとMACDの計算
    data = calculate_indicators(data)
    
    # 過去10日の分析
    analyze_recent_data(data, fund_title, days=100)

    # 7日間のチャート表示を追加
    draw_recent_chart(data, fund_title, days=25)


if __name__ == "__main__":
    main()

    