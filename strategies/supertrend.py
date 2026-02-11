import pandas as pd
import numpy as np

def calculate_supertrend(df, period=10, multiplier=3):
    """
    Menghitung Indikator Supertrend secara manual.
    Period: 10 (Standar)
    Multiplier: 3 (Semakin besar, semakin jarang sinyal tapi semakin akurat tren besar)
    """
    df = df.copy()
    
    # 1. Hitung ATR (Average True Range)
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()

    # 2. Hitung Basic Upper & Lower Bands
    # Basic Upper = (High + Low) / 2 + (Multiplier * ATR)
    # Basic Lower = (High + Low) / 2 - (Multiplier * ATR)
    hl2 = (df['High'] + df['Low']) / 2
    df['Basic_Upper'] = hl2 + (multiplier * df['ATR'])
    df['Basic_Lower'] = hl2 - (multiplier * df['ATR'])

    # 3. Hitung Final Upper & Lower Bands (Looping)
    # Aturan: Final Band tidak boleh menjauh dari harga, hanya boleh mendekat atau datar.
    
    final_upper = [0.0] * len(df)
    final_lower = [0.0] * len(df)
    supertrend = [0.0] * len(df)
    trend_dir = [1] * len(df) # 1: Uptrend (Green), -1: Downtrend (Red)
    
    # Inisialisasi
    for i in range(len(df)):
        if i == 0:
            final_upper[i] = df['Basic_Upper'].iloc[i]
            final_lower[i] = df['Basic_Lower'].iloc[i]
            continue

        prev_final_upper = final_upper[i-1]
        prev_final_lower = final_lower[i-1]
        prev_close = df['Close'].iloc[i-1]
        
        # Kalkulasi Final Upper
        if (df['Basic_Upper'].iloc[i] < prev_final_upper) or (prev_close > prev_final_upper):
            final_upper[i] = df['Basic_Upper'].iloc[i]
        else:
            final_upper[i] = prev_final_upper
            
        # Kalkulasi Final Lower
        if (df['Basic_Lower'].iloc[i] > prev_final_lower) or (prev_close < prev_final_lower):
            final_lower[i] = df['Basic_Lower'].iloc[i]
        else:
            final_lower[i] = prev_final_lower
            
    # 4. Tentukan Arah Trend (Supertrend Logic)
    for i in range(1, len(df)):
        prev_trend = trend_dir[i-1]
        prev_st = supertrend[i-1]
        curr_close = df['Close'].iloc[i]
        
        if prev_trend == 1: # Sedang Uptrend
            if curr_close < final_lower[i]:
                trend_dir[i] = -1 # Ganti jadi Downtrend
            else:
                trend_dir[i] = 1
        else: # Sedang Downtrend
            if curr_close > final_upper[i]:
                trend_dir[i] = 1 # Ganti jadi Uptrend
            else:
                trend_dir[i] = -1
        
        # Set nilai Supertrend Line
        if trend_dir[i] == 1:
            supertrend[i] = final_lower[i]
        else:
            supertrend[i] = final_upper[i]
            
    df['Supertrend'] = supertrend
    df['Trend_Dir'] = trend_dir
    
    return df

def apply_strategy(df):
    """
    Strategi Supertrend Murni.
    Buy: Saat Trend berubah jadi 1 (Hijau/Uptrend)
    Sell: Saat Trend berubah jadi -1 (Merah/Downtrend)
    """
    df = calculate_supertrend(df, period=10, multiplier=3)
    
    df['Signal'] = 0
    
    # Deteksi Perubahan Tren
    # Trend Sekarang 1 DAN Trend Kemarin -1 => BUY
    buy_cond = (df['Trend_Dir'] == 1) & (df['Trend_Dir'].shift(1) == -1)
    
    # Trend Sekarang -1 DAN Trend Kemarin 1 => SELL
    sell_cond = (df['Trend_Dir'] == -1) & (df['Trend_Dir'].shift(1) == 1)
    
    df.loc[buy_cond, 'Signal'] = 1
    df.loc[sell_cond, 'Signal'] = -1
    
    # Ffill Logic untuk Holding
    current_signal = 0
    signal_col = []
    
    for i in range(len(df)):
        s = df['Signal'].iloc[i]
        if s == 1: current_signal = 1
        elif s == -1: current_signal = 0
        signal_col.append(current_signal)
        
    df['Signal'] = signal_col
    
    return df