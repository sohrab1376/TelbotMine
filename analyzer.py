import requests
import pandas as pd

def fetch_klines(symbol='BTCUSDT', interval='15m', limit=1000):
    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    data = requests.get(url, params=params).json()
    df = pd.DataFrame(data, columns=[
        'Open Time','Open','High','Low','Close','Volume',
        'Close Time','Quote Asset Volume','Number of Trades',
        'Taker buy base','Taker buy quote','Ignore'
    ])
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    for c in ['Open','High','Low','Close','Volume']:
        df[c] = df[c].astype(float)
    return df

def calculate_indicators(df):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['EMA100'] = df['Close'].ewm(span=100).mean()
    df['SMA20'] = df['Close'].rolling(20).mean()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_g = gain.rolling(14).mean()
    avg_l = loss.rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (avg_g/avg_l)))
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9).mean()
    tr = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low'] - df['Close'].shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR14'] = tr.shift(1).rolling(14).mean()
    df['Momentum10'] = df['Close'] - df['Close'].shift(10)
    high14 = df['High'].rolling(14).max()
    low14 = df['Low'].rolling(14).min()
    df['WR'] = -100 * (high14 - df['Close']) / (high14 - low14)
    return df

def detect_pivots(df):
    highs = df['High'].values
    lows = df['Low'].values
    ph, pl = [], []
    for i in range(5, len(df) - 5):
        if highs[i] == max(highs[i - 5:i + 6]):
            ph.append(i)
        if lows[i] == min(lows[i - 5:i + 6]):
            pl.append(i)
    df['pivot_high'] = False
    df['pivot_low'] = False
    df.loc[ph, 'pivot_high'] = True
    df.loc[pl, 'pivot_low'] = True
    return df

def apply_filter_a(df, i, direction, a):
    pos = df.index.get_loc(i)
    atr = df.at[i, 'ATR14']
    entry = df.at[i, 'Close']
    sub = df.iloc[:pos]
    if direction == 'long':
        prev = sub[(sub['pivot_high']) & (sub['High'] > entry)]
        if prev.empty: return False
        j = prev.index[-1]
        dist = df.at[j, 'High'] - entry
    else:
        prev = sub[(sub['pivot_low']) & (sub['Low'] < entry)]
        if prev.empty: return False
        j = prev.index[-1]
        dist = entry - df.at[j, 'Low']
    return dist >= a * atr

def apply_filter_b(df, i, direction, b):
    pos = df.index.get_loc(i)
    atr = df.at[i, 'ATR14']
    entry = df.at[i, 'Close']
    sub = df.iloc[:pos]
    if direction == 'long':
        highs = sub[sub['pivot_high']]
        if len(highs) < 2: return False
        p2 = highs.index[-1]
        candidates = [idx for idx in highs.index[:-1] if df.at[idx, 'High'] > df.at[p2, 'High']]
        if not candidates: return False
        p1 = candidates[-1]
        y1, y2 = df.at[p1, 'High'], df.at[p2, 'High']
        idx1, idx2 = df.index.get_loc(p1), df.index.get_loc(p2)
        slope = (y2 - y1) / (idx2 - idx1)
        proj = y2 + slope * (pos - idx2)
        dist = entry - proj
        ok = entry > proj
    else:
        lows = sub[sub['pivot_low']]
        if len(lows) < 2: return False
        p2 = lows.index[-1]
        candidates = [idx for idx in lows.index[:-1] if df.at[idx, 'Low'] < df.at[p2, 'Low']]
        if not candidates: return False
        p1 = candidates[-1]
        y1, y2 = df.at[p1, 'Low'], df.at[p2, 'Low']
        idx1, idx2 = df.index.get_loc(p1), df.index.get_loc(p2)
        slope = (y2 - y1) / (idx2 - idx1)
        proj = y2 + slope * (pos - idx2)
        dist = proj - entry
        ok = entry < proj
    return ok and (dist >= b * atr)

def get_directional_signal(df, combo, i):
    pos = df.index.get_loc(i)
    long_sig = True
    short_sig = True
    for ind in combo:
        if ind == 3:
            r = df.at[i, 'RSI']
            long_sig &= 50 < r < 70
            short_sig &= 30 < r < 50
        elif ind == 8:
            long_sig &= df.at[i, 'MACD'] > 0
            short_sig &= df.at[i, 'MACD'] < 0
        elif ind == 10:
            long_sig &= df.at[i, 'WR'] > -50
            short_sig &= df.at[i, 'WR'] <= -50
        elif ind == 11:
            long_sig &= df.at[i, 'Momentum10'] > 0
            short_sig &= df.at[i, 'Momentum10'] < 0
    return 'long' if long_sig else 'short' if short_sig else None

def analyze_last_candle(a, b, combos):
    df = fetch_klines()
    df = calculate_indicators(df)
    df = detect_pivots(df)
    i = df.index[-1]
    for combo in combos:
        d = get_directional_signal(df, combo, i)
        if not d:
            continue
        fa = apply_filter_a(df, i, d, a)
        fb = apply_filter_b(df, i, d, b)
        if fa and fb:
            entry = df.at[i, 'Close']
            atr = df.at[i, 'ATR14']
            tp = entry + 1.5 * atr if d == 'long' else entry - 1.5 * atr
            sl = entry - 1.0 * atr if d == 'long' else entry + 1.0 * atr
            loss_pct = abs(entry - sl) / entry
            lev = round(0.03 / loss_pct, 2)
            return {
                'direction': d,
                'entry': entry,
                'tp': tp,
                'sl': sl,
                'atr': atr,
                'leverage': lev
            }
    return None