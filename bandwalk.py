import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from decimal import Decimal, getcontext
import warnings
warnings.filterwarnings('ignore')

# 精度設定
getcontext().prec = 28

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

def load_and_prepare_data(filename, fund_title):
    """CSVファイルを読み込んで前処理を行う"""
    try:
        # CSVファイル読み込み
        df = pd.read_csv(filename, encoding='utf-8')
        
        # 列名を標準化
        df.columns = ['date', 'nav', 'daily_change', 'total_assets']
        
        # 日付をdatetimeに変換
        df['date'] = pd.to_datetime(df['date'])
        
        # 数値データを適切な型に変換
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        df['daily_change'] = pd.to_numeric(df['daily_change'], errors='coerce')
        
        # NAVをDecimalに変換
        df['nav_decimal'] = df['nav'].apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
        
        # データを日付順にソート
        df = df.sort_values('date').reset_index(drop=True)
        
        colored_print(f"=== {fund_title} ===", Colors.BOLD + Colors.MAGENTA)
        colored_print(f"データロード完了: {len(df)}日分のデータ", Colors.GREEN)
        colored_print(f"データ期間: {df['date'].min().strftime('%Y/%m/%d')} ～ {df['date'].max().strftime('%Y/%m/%d')}", Colors.BLUE)
        
        return df
        
    except Exception as e:
        colored_print(f"データロードエラー: {e}", Colors.RED)
        return None

def calculate_bollinger_bands(df):
    """ボリンジャーバンドと移動平均を計算"""
    
    # 20日移動平均（中央線）
    df['sma_20'] = df['nav'].rolling(window=BB_PERIOD).mean()
    
    # 20日標準偏差
    df['std_20'] = df['nav'].rolling(window=BB_PERIOD).std()
    
    # ボリンジャーバンド上限・下限
    df['bb_upper'] = df['sma_20'] + (BB_STD * df['std_20'])
    df['bb_lower'] = df['sma_20'] - (BB_STD * df['std_20'])
    
    # 25日移動平均
    df['ma25'] = df['nav'].rolling(window=MA25_PERIOD).mean()
    
    # Decimal版も作成
    for col in ['sma_20', 'bb_upper', 'bb_lower', 'ma25']:
        df[f'{col}_decimal'] = df[col].apply(lambda x: Decimal(str(x)) if pd.notna(x) else Decimal('0'))
    
    return df

def calculate_band_position(price, bb_upper, bb_lower):
    """バンド内での相対位置を計算（0=下限, 1=上限）"""
    if bb_upper != bb_lower:
        position = (price - bb_lower) / (bb_upper - bb_lower)
    else:
        position = Decimal('0.5')
    return position

def check_band_walk(df, current_idx):
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
        
        check_price = df.iloc[idx]['nav_decimal']
        check_bb_upper = df.iloc[idx]['bb_upper_decimal']
        check_bb_lower = df.iloc[idx]['bb_lower_decimal']
        
        # バンド内位置を計算
        position = calculate_band_position(check_price, check_bb_upper, check_bb_lower)
        positions.append(float(position))
        
        # 上限付近（85%以上）かチェック
        if position >= Decimal('0.85'):
            upper_walk_count += 1
        
        # 下限付近（15%以下）かチェック
        if position <= Decimal('0.15'):
            lower_walk_count += 1
    
    # 現在の状態
    current_price = df.iloc[current_idx]['nav_decimal']
    current_bb_upper = df.iloc[current_idx]['bb_upper_decimal']
    current_bb_lower = df.iloc[current_idx]['bb_lower_decimal']
    current_ma25 = df.iloc[current_idx]['ma25_decimal']
    
    current_position = calculate_band_position(current_price, current_bb_upper, current_bb_lower)
    current_above_ma = current_price > current_ma25
    current_below_ma = current_price < current_ma25
    
    avg_position = sum(positions) / len(positions)
    
    # 上昇バンドウォーク判定
    if upper_walk_count == lookback and avg_position >= 0.85 and current_above_ma:
        if current_position < Decimal('0.7'):
            return 'sell', f'上昇バンドウォーク（{lookback-1}日継続）からの剥離', True
        else:
            return 'hold', f'上昇バンドウォーク継続中（{lookback-1}日継続）', True
    
    # 下降バンドウォーク判定
    if lower_walk_count == lookback and avg_position <= 0.15 and current_below_ma:
        if current_position > Decimal('0.3'):
            return 'buy', f'下降バンドウォーク（{lookback-1}日継続）からの剥離', True
        else:
            return 'hold', f'下降バンドウォーク継続中（{lookback-1}日継続）', True
    
    return 'normal', '通常状態', False

def analyze_recent_data(df, fund_title, days=10):
    """過去N日の分析結果を表示"""
    colored_print(f"\n=== {fund_title} - 過去{days}日の分析結果 ===", Colors.BOLD + Colors.MAGENTA)
    colored_print("-" * 80, Colors.WHITE)
    
    # 最新のデータから過去N日分を取得
    recent_df = df.tail(days).copy()
    
    for idx, row in recent_df.iterrows():
        original_idx = df.index[df['date'] == row['date']].tolist()[0]
        
        # バンドウォーク判定
        action, message, is_bandwalk = check_band_walk(df, original_idx)
        
        # バンド内位置
        position = calculate_band_position(
            row['nav_decimal'], 
            row['bb_upper_decimal'], 
            row['bb_lower_decimal']
        )
        
        # データの型チェックと変換
        nav_value = float(row['nav']) if pd.notna(row['nav']) else 0.0
        daily_change_value = float(row['daily_change']) if pd.notna(row['daily_change']) else 0.0
        bb_upper_value = float(row['bb_upper']) if pd.notna(row['bb_upper']) else 0.0
        bb_lower_value = float(row['bb_lower']) if pd.notna(row['bb_lower']) else 0.0
        
        # バンドとの価格差
        upper_diff = bb_upper_value - nav_value
        lower_diff = nav_value - bb_lower_value
        
        # 状態表示
        status_color = "🔴" if action == "sell" else "🟢" if action == "buy" else "⚪"
        bandwalk_mark = "🚨" if is_bandwalk else ""
        
        # 日付表示（色付き）
        date_str = row['date'].strftime('%Y/%m/%d')
        colored_print(f"{fund_title} {date_str} {status_color}{bandwalk_mark}", Colors.BOLD + Colors.CYAN)
        
        # 価格表示
        change_color = Colors.RED if daily_change_value < 0 else Colors.GREEN if daily_change_value > 0 else Colors.WHITE
        print(f"価格: {nav_value:,.0f}円 ", end="")
        colored_print(f"(前日比: {daily_change_value:+.0f}円)", change_color)
        
        # バンド位置表示（色分け）
        position_value = float(position)
        if position_value > 1.0:
            position_color = Colors.RED
            position_status = "⚠️ 上限突破!"
        elif position_value < 0.0:
            position_color = Colors.RED
            position_status = "⚠️ 下限突破!"
        elif position_value >= 0.85:
            position_color = Colors.YELLOW
            position_status = "⚠️ 上限付近"
        elif position_value <= 0.15:
            position_color = Colors.CYAN
            position_status = "⚠️ 下限付近"
        else:
            position_color = Colors.WHITE
            position_status = ""
        
        print(f"  バンド位置: ", end="")
        colored_print(f"{position_value:.3f} (0=下限, 1=上限) {position_status}", position_color)
        
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

def create_bandwalk_chart(df, fund_title, output_filename="bandwalk_chart.png"):
    """バンドウォーク区間を色付けしたチャートを作成 - 過去500日のデータを使用"""
    
    # 過去500日のデータを取得
    chart_df = df.tail(500).copy().reset_index(drop=True)
    
    # colored_print(f"チャート作成中: 過去{len(chart_df)}日分のデータを使用", Colors.BLUE)
    
    # バンドウォーク状態を判定（元のデータフレームのインデックスを使用）
    market_states = ['normal'] * len(chart_df)
    
    for i in range(len(chart_df)):
        # 元のデータフレームでのインデックスを取得
        original_idx = df.index[df['date'] == chart_df.iloc[i]['date']].tolist()[0]
        action, message, is_bandwalk = check_band_walk(df, original_idx)
        
        if is_bandwalk:
            # 過去5日間をまとめてband_walk状態に設定
            for j in range(BAND_WALK_DAYS):
                if i - j >= 0:
                    market_states[i - j] = 'band_walk'
    
    # グラフ作成
    plt.rcParams['font.size'] = 10
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # 日付とデータの準備
    dates = chart_df['date']
    prices = chart_df['nav']
    bb_upper = chart_df['bb_upper']
    bb_lower = chart_df['bb_lower']
    sma_20 = chart_df['sma_20']
    
    # 背景色の設定（バンドウォーク区間）
    bandwalk_labeled = False
    for i in range(len(dates)):
        if market_states[i] == 'band_walk':
            start_date = dates.iloc[max(0, i-1)]
            end_date = dates.iloc[min(len(dates)-1, i+1)]
            label = 'Band Walk' if not bandwalk_labeled else ''
            ax.axvspan(start_date, end_date, alpha=0.2, color='red', label=label)
            bandwalk_labeled = True
    
    # ボリンジャーバンドの描画
    ax.plot(dates, bb_upper, color='gray', linestyle='--', alpha=0.7, label='Upper Band (+2σ)', linewidth=1)
    ax.plot(dates, bb_lower, color='gray', linestyle='--', alpha=0.7, label='Lower Band (-2σ)', linewidth=1)
    ax.plot(dates, sma_20, color='blue', linestyle='-', alpha=0.5, label='Middle Line (20-day MA)', linewidth=1)
    
    # 価格の描画
    ax.plot(dates, prices, color='black', linewidth=1.5, label='NAV')
    
    # グラフの装飾（ファンドタイトルを含める）
    ax.set_title(f'{fund_title} - Bollinger Bands with Band Walk Detection (Past 500 Days)', fontsize=16, pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('NAV (Yen)', fontsize=12)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # x軸の日付表示を調整
    ax.tick_params(axis='x', rotation=45)
    
    # x軸の日付間隔を調整（データ量に応じて）
    if len(chart_df) > 500:
        # 大量データの場合は年単位で目盛りを設定
        import matplotlib.dates as mdates
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 4, 7, 10)))
    
    # レイアウト調整
    plt.tight_layout()
    
    # PNG出力
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    # colored_print(f"チャートを保存しました: {output_filename}", Colors.GREEN)
    
    # plt.show()

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
    df = load_and_prepare_data(filename, fund_title)
    
    if df is None:
        return
    
    # ボリンジャーバンドの計算
    df = calculate_bollinger_bands(df)
    
    # 過去10日の分析
    analyze_recent_data(df, fund_title, days=10)
    
    # チャート作成（過去500日使用）
    create_bandwalk_chart(df, fund_title, output_filename=f"{output_dir_base}/{id}_{datetime.now().strftime('%Y-%m-%d')}.png")

if __name__ == "__main__":
    main()