import pandas as pd
import numpy as np

def apply_strategy(df):
    """
    Strategi Mean Reversion: Bollinger Bands + RSI
    
    UPDATE LOGIKA:
    - Entry: Close < Lower Band DAN RSI < 30
    - Exit : Close > Upper Band DAN RSI > 70 (Wajib Keduanya)
    """
    df = df.copy()
    
    # --- 1. SETTING PARAMETER ---
    bb_period = 20      
    bb_std_dev = 2.0    
    rsi_period = 14     
    rsi_lower = 30      
    rsi_upper = 70      

    # --- 2. HITUNG INDIKATOR ---
    
    # A. Hitung Bollinger Bands
    df['SMA_20'] = df['Close'].rolling(window=bb_period).mean()
    df['Std_Dev'] = df['Close'].rolling(window=bb_period).std()
    df['BB_Upper'] = df['SMA_20'] + (bb_std_dev * df['Std_Dev'])
    df['BB_Lower'] = df['SMA_20'] - (bb_std_dev * df['Std_Dev'])
    
    # B. Hitung RSI (Rumus Manual Pandas)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(com=rsi_period-1, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(com=rsi_period-1, min_periods=rsi_period).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # --- 3. LOGIKA SINYAL (SIGNAL LOGIC) ---
    
    df['Signal'] = np.nan 

    # KONDISI BUY (Tetap sama)
    # Harga murah banget (Tembus Bawah) DAN Oversold
    buy_condition = (df['Close'] < df['BB_Lower']) & (df['RSI'] < rsi_lower)
    
    # KONDISI SELL (YANG DIUBAH)
    # Dulu: Pakai | (OR) -> Salah satu terpenuhi langsung jual.
    # Sekarang: Pakai & (AND) -> Dua-duanya WAJIB terpenuhi baru jual.
    sell_condition = (df['Close'] > df['BB_Upper']) & (df['RSI'] > rsi_upper)

    # Terapkan Sinyal
    df.loc[buy_condition, 'Signal'] = 1
    df.loc[sell_condition, 'Signal'] = 0
    
    # Forward Fill (Pertahankan posisi sampai sinyal berubah)
    df['Signal'] = df['Signal'].ffill().fillna(0)
    
    return df