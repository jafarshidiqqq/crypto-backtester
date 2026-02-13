import ccxt
import pandas as pd
import time
import streamlit as st

def get_binance_data(symbol, timeframe, start_date):
    """
    Mengambil data OHLCV dari BINANCE.
    """
    try:
        # Inisialisasi Binance
        exchange = ccxt.binance({
            'enableRateLimit': True,
            # 'timeout': 30000, 
        })
        
        # Konversi Start Date
        since = exchange.parse8601(start_date)
        
        all_candles = []
        limit = 1000 
        
        # UI Progress
        progress_text = f"Mengambil data {symbol} dari Binance..."
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
                total = len(all_candles)
                my_bar.progress(min(total % 100, 100), text=f"Terkumpul: {total} candles...")
                
                if len(candles) < limit:
                    break
                    
            except Exception as e:
                time.sleep(1) # Retry logic
                continue
        
        my_bar.empty()

        if not all_candles:
            return pd.DataFrame()

        # Format DataFrame
        df = pd.DataFrame(all_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Timestamp', inplace=True)
        
        return df

    except Exception as e:
        return pd.DataFrame()
