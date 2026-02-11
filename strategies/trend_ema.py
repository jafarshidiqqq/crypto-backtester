import pandas as pd
import numpy as np

def calculate_adx(df, period=14):
    """
    Fungsi bantuan untuk menghitung ADX (Kekuatan Tren) secara manual
    """
    df = df.copy()
    
    # 1. Hitung True Range (TR)
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    
    # 2. Directional Movement (DM)
    df['UpMove'] = df['High'] - df['High'].shift(1)
    df['DownMove'] = df['Low'].shift(1) - df['Low']
    
    df['+DM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['-DM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)
    
    # 3. Smoothed TR and DM (Wilder's Smoothing)
    # Fungsi manual untuk smoothing mirip tradingview
    def wilder_smooth(series, period):
        res = [np.nan] * len(series)
        # Initial value: Simple Moving Average
        if len(series) > period:
            res[period-1] = series.iloc[0:period].mean() 
            for i in range(period, len(series)):
                res[i] = res[i-1] - (res[i-1]/period) + series.iloc[i]
        return res

    df['TR14'] = wilder_smooth(df['TR'], period)
    df['+DM14'] = wilder_smooth(df['+DM'], period)
    df['-DM14'] = wilder_smooth(df['-DM'], period)

    # 4. DI+ dan DI-
    df['+DI'] = 100 * (df['+DM14'] / df['TR14'])
    df['-DI'] = 100 * (df['-DM14'] / df['TR14'])
    
    # 5. ADX
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])
    df['ADX'] = pd.Series(wilder_smooth(df['DX'], period), index=df.index)
    
    return df['ADX']

def apply_strategy(df):
    """
    Strategi: Triple EMA Trend + ADX Filter (Revised)
    
    Perbaikan:
    - Menambahkan ADX Filter: Hanya trade jika ADX > 20 (Tren Kuat).
    - Menghapus Exit Signal EMA Cross Down yang terlalu sensitif.
    - Exit hanya mengandalkan SL/TP atau Patah Tren Utama (Close < EMA 50).
    """
    df = df.copy()
    
    # --- 1. HITUNG INDIKATOR ---
    df['EMA_8'] = df['Close'].ewm(span=8, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean() # Ganti 200 jadi 50 biar lebih responsif
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # ADX (Filter Kekuatan Tren)
    df['ADX'] = calculate_adx(df)

    # --- 2. LOGIKA SIGNAL ---
    df['Signal'] = 0
    
    crossover_up = (df['EMA_8'] > df['EMA_21']) & (df['EMA_8'].shift(1) <= df['EMA_21'].shift(1))
    
    # --- LOGIKA ENTRY (BUY) ---
    # Syarat Diperketat:
    # 1. Tren Besar Bullish (Harga > EMA 200)
    # 2. Golden Cross (8 memotong 21)
    # 3. Momentum RSI Bagus (50-70)
    # 4. ADX > 20 (WAJIB ADA TREN KUAT, JANGAN SIDEWAYS)
    
    buy_condition = (
        (df['Close'] > df['EMA_200']) &    
        crossover_up &                     
        (df['RSI'] > 50) &                 
        (df['RSI'] < 70) &
        (df['ADX'] > 20)  # <--- Filter Baru "Anti Sideways"
    )
    
    # --- LOGIKA EXIT (SELL) ---
    # Exit diperlonggar: Jangan keluar cuma gara-gara cross down kecil.
    # Keluar hanya jika harga jebol EMA 50 (Tren jangka menengah rusak)
    
    sell_condition = (df['Close'] < df['EMA_50'])
    
    # Terapkan Sinyal
    df.loc[buy_condition, 'Signal'] = 1
    df.loc[sell_condition, 'Signal'] = -1
    
    # Loop Manual untuk State Holding
    current_signal = 0
    signal_col = []
    
    for i in range(len(df)):
        signal_val = df['Signal'].iloc[i]
        
        if signal_val == 1: 
            current_signal = 1
        elif signal_val == -1: 
            current_signal = 0
            
        signal_col.append(current_signal)
        
    df['Signal'] = signal_col
    
    return df