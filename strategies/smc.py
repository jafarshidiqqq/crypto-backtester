import pandas as pd
import numpy as np

def apply_strategy(df):
    """
    Smart Money Concept (SMC) Strategy
    
    Konsep:
    1. Identifikasi Swing High/Low (Fractals).
    2. Deteksi Break of Structure (BOS).
    3. Tandai Order Block (OB) yang menyebabkan BOS.
    4. Entry saat harga kembali (Mitigation) ke area OB tersebut.
    """
    df = df.copy()
    
    # --- 1. IDENTIFIKASI SWING (FRACTALS) ---
    # Window 2 kiri, 2 kanan (Total 5 candle)
    # Kita pakai shift(-2) karena swing baru valid 2 candle setelahnya
    
    df['Swing_High'] = df['High'].rolling(window=5, center=True).max()
    df['Swing_Low'] = df['Low'].rolling(window=5, center=True).min()
    
    # Is_Swing: Boolean jika candle i adalah puncak/lembah
    # Perlu shift(2) untuk mengembalikan ke posisi asli karena rolling center=True sempat 'mengintip' ke depan
    # Namun dalam trading real-time, kita baru tahu itu swing di candle i+2.
    # Jadi kita tandai swing di titik kejadiannya, tapi logikanya baru bisa dipakai nanti.
    
    df['Is_Swing_High'] = (df['High'] == df['Swing_High'])
    df['Is_Swing_Low'] = (df['Low'] == df['Swing_Low'])

    # --- 2. LOGIKA UTAMA (LOOP) ---
    # Kita butuh loop karena harus menyimpan daftar Order Block yang "Hidup"
    
    signals = np.zeros(len(df))
    
    # State Variables
    last_swing_high_price = 0
    last_swing_low_price = 0
    last_swing_high_idx = 0
    last_swing_low_idx = 0
    
    # List Order Blocks [Price_Top, Price_Bottom, Type(1/-1), Mitigated(Bool)]
    active_obs = [] 
    
    # Loop dimulai dari candle ke-5
    for i in range(5, len(df)):
        current_close = df['Close'].iloc[i]
        current_low = df['Low'].iloc[i]
        current_high = df['High'].iloc[i]
        current_open = df['Open'].iloc[i]
        
        # A. UPDATE SWING (Hanya update jika swing sudah terkonfirmasi 2 bar lalu)
        # Kita cek index i-2 apakah dia swing
        check_idx = i - 2
        if df['Is_Swing_High'].iloc[check_idx]:
            last_swing_high_price = df['High'].iloc[check_idx]
            last_swing_high_idx = check_idx
            
        if df['Is_Swing_Low'].iloc[check_idx]:
            last_swing_low_price = df['Low'].iloc[check_idx]
            last_swing_low_idx = check_idx

        # B. DETEKSI BOS & PEMBUATAN ORDER BLOCK
        
        # --- BULLISH BOS (Harga Close tembus Swing High Terakhir) ---
        if last_swing_high_price > 0 and current_close > last_swing_high_price:
            # Pastikan ini fresh breakout (bar sebelumnya belum tembus)
            if df['Close'].iloc[i-1] <= last_swing_high_price:
                # BOS Terjadi! Cari Bullish OB.
                # Cari candle merah terakhir di antara Swing Low terakhir dan Breakout ini
                search_start = last_swing_low_idx
                search_end = i
                
                # Slice data range tersebut
                range_df = df.iloc[search_start:search_end]
                # Filter candle merah (Close < Open)
                red_candles = range_df[range_df['Close'] < range_df['Open']]
                
                if not red_candles.empty:
                    # Ambil candle merah TERAKHIR sebelum naik
                    ob_candle = red_candles.iloc[-1]
                    
                    # Definisi Zone OB: Dari Low sampai High candle tersebut
                    ob_top = ob_candle['High']
                    ob_bottom = ob_candle['Low']
                    
                    # Simpan ke list: [Top, Bottom, Tipe=1 (Buy), Mitigated=False]
                    active_obs.append({'top': ob_top, 'bottom': ob_bottom, 'type': 1, 'mitigated': False})

        # --- BEARISH BOS (Harga Close tembus Swing Low Terakhir) ---
        if last_swing_low_price > 0 and current_close < last_swing_low_price:
            if df['Close'].iloc[i-1] >= last_swing_low_price:
                # BOS Bearish! Cari Bearish OB (Candle Hijau Terakhir)
                search_start = last_swing_high_idx
                search_end = i
                
                range_df = df.iloc[search_start:search_end]
                green_candles = range_df[range_df['Close'] > range_df['Open']]
                
                if not green_candles.empty:
                    ob_candle = green_candles.iloc[-1]
                    ob_top = ob_candle['High']
                    ob_bottom = ob_candle['Low']
                    
                    # Simpan: [Top, Bottom, Tipe=-1 (Sell), Mitigated=False]
                    active_obs.append({'top': ob_top, 'bottom': ob_bottom, 'type': -1, 'mitigated': False})

        # C. CEK MITIGATION (ENTRY SIGNAL)
        # Kita cek apakah harga sekarang menyentuh salah satu OB yang masih aktif
        
        signal = 0
        
        for ob in active_obs:
            if ob['mitigated']:
                continue # Skip OB yang sudah kepakai
            
            # Cek Bullish OB (Area Buy)
            if ob['type'] == 1:
                # Jika Low hari ini menyentuh zona OB (tapi Close jangan jebol bawah OB biar aman)
                if current_low <= ob['top'] and current_close >= ob['bottom']:
                    signal = 1
                    ob['mitigated'] = True # Tandai sudah dipakai (sekali pakai)
            
            # Cek Bearish OB (Area Sell)
            elif ob['type'] == -1:
                # Jika High hari ini menyentuh zona OB
                if current_high >= ob['bottom'] and current_close <= ob['top']:
                    signal = -1 # Sinyal Sell tidak disupport backtester sederhana kita (Hanya Buy/Exit),
                                # Tapi kita bisa pakai untuk Close Position Long
                    ob['mitigated'] = True

        signals[i] = signal

    df['Signal'] = signals
    
    # Forward Fill Signal (Opsional, tapi untuk SMC biasanya entry di titik sentuh)
    # Kita biarkan 0 jika tidak ada sinyal, agar backtester pakai logic hold
    
    # TAPI: Backtester kita butuh state 1 untuk Hold.
    # Jadi kita ubah: Jika Signal 1 (Buy), set state jadi 1. 
    # Jika Signal -1 (Kena Bearish OB), set state jadi 0 (Sell).
    
    df['Signal'] = df['Signal'].replace(0, np.nan).ffill().fillna(0)
    
    # Ubah -1 menjadi 0 untuk kompatibilitas backtester (0 = Cash)
    df['Signal'] = df['Signal'].apply(lambda x: 1 if x == 1 else 0)
    
    return df