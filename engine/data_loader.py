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
            'timeout': 30000, 
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
                my_bar.progress(min(len(all_candles) % 100, 100), text=f"⏳ Terkumpul: {len(all_candles)} candles...")
                
                if len(candles) < limit:
                    break
                    
            except Exception as e:
                time.sleep(1) # Retry logic
                continue
        
        my_bar.empty()

        if not all_candles:
            st.error(f"❌ Data {symbol} kosong atau gagal diambil dari Binance.")
            return pd.DataFrame()

        # Format DataFrame
        df = pd.DataFrame(all_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Timestamp', inplace=True)
        
        return df

    except Exception as e:
        st.error(f"Error Data Loader: {str(e)}")
        return pd.DataFrame()
