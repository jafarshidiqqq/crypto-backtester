import ccxt
import pandas as pd
import time
import streamlit as st

# --- JURUS 1: DEKORATOR CACHE ---
# ttl=3600 artinya data disimpan di memori selama 1 jam (3600 detik)
# show_spinner=False biar loading bar kita sendiri yang muncul
@st.cache_data(ttl=3600, show_spinner=False)
def get_binance_data(symbol, timeframe, start_date):
    """
    Mengambil data OHLCV dari BINANCE dengan CACHING.
    """
    try:
        # Inisialisasi Binance
        exchange = ccxt.binance({
            'enableRateLimit': True, # Wajib True biar ga kena Banned
            # 'timeout': 30000, 
        })
        
        # Konversi Start Date
        since = exchange.parse8601(start_date)
        
        all_candles = []
        limit = 1000 # Max limit Binance per request
        
        # UI Progress (Kita taruh di placeholder biar tidak duplikat saat caching)
        progress_text = f"📥 Sedang mengunduh data {symbol}..."
        my_bar = st.progress(0, text=progress_text)
        
        while True:
            try:
                # Fetch Data
                candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Update Next Timestamp
                last_time = candles[-1][0]
                since = last_time + 1
                
                # Update UI
                # (Tips: Biar ga berat, update progress setiap 1000 data aja)
                total = len(all_candles)
                my_bar.progress(min(total % 100, 100), text=f"⏳ Terkumpul: {total} candles...")
                
                if len(candles) < limit:
                    break
                    
            except Exception as e:
                time.sleep(1) # Retry logic
                continue
        
        my_bar.empty() # Hapus loading bar setelah selesai

        if not all_candles:
            return pd.DataFrame()

        # Format DataFrame
        df = pd.DataFrame(all_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Timestamp', inplace=True)
        
        return df

    except Exception as e:
        # st.error dihapus biar ga ngerusak UI cache
        return pd.DataFrame()
