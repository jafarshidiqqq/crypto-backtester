import ccxt
import pandas as pd
import time
import streamlit as st

# Perhatikan baris di bawah ini: harus ada exchange_id='kraken'
def get_binance_data(symbol, timeframe, start_date, exchange_id='kraken'):
    try:
        # Inisialisasi Exchange (Default Kraken biar tembus server US)
        if exchange_id == 'binance':
            exchange = ccxt.binance({'enableRateLimit': True})
        else:
            # Force Kraken kalau tidak spesifik minta Binance
            exchange = ccxt.kraken({'enableRateLimit': True})
            
            # Auto-convert simbol USDT ke USD (karena Kraken jarangan pair USDT)
            if 'USDT' in symbol:
                symbol = symbol.replace('USDT', 'USD')

        since = exchange.parse8601(start_date)
        all_candles = []
        limit = 720 # Limit aman
        
        # Loop download data
        while True:
            try:
                candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                if not candles: break
                
                all_candles.extend(candles)
                since = candles[-1][0] + 1
                
                if len(candles) < limit: break
                
            except Exception:
                time.sleep(1) # Rehat bentar kalau koneksi putus
                continue
                
        if not all_candles:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Timestamp', inplace=True)
        return df

    except Exception as e:
        return pd.DataFrame()
