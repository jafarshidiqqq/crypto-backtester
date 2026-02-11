import ccxt
import pandas as pd
import os
from dotenv import load_dotenv
import time

load_dotenv()

def get_binance_data(symbol, timeframe='1h', start_date='2020-01-01 00:00:00'):
    """
    Mengambil data LENGKAP dari start_date sampai sekarang dengan teknik Pagination.
    """
    
    # 1. Inisialisasi Exchange (Jalur Publik)
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'} 
    })

    # Konversi tanggal mulai ke Timestamp (milidetik)
    since = exchange.parse8601(start_date)
    
    all_ohlcv = []
    
    print(f"📥 Memulai download data {symbol} ({timeframe}) sejak {start_date}...")
    print("⏳ Mohon tunggu, proses ini butuh waktu karena mengambil data bertahun-tahun...")

    while True:
        try:
            # Ambil 1000 candle mulai dari waktu 'since'
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            
            # Jika tidak ada data lagi, berhenti
            if len(ohlcv) == 0:
                break
            
            # Gabungkan data
            all_ohlcv.extend(ohlcv)
            
            # Update waktu 'since' menjadi waktu candle terakhir + 1 milidetik
            # Agar request berikutnya mengambil data LANJUTANNYA
            last_candle_time = ohlcv[-1][0]
            since = last_candle_time + 1
            
            print(f"   ... Terambil {len(all_ohlcv)} candle sejauh ini (Last: {pd.to_datetime(last_candle_time, unit='ms')})")
            
            # Jika data yang diambil kurang dari 1000, berarti sudah sampai ujung (hari ini)
            if len(ohlcv) < 1000:
                break
                
        except Exception as e:
            print(f"Error saat looping: {e}")
            break

    # Rapikan ke DataFrame
    if len(all_ohlcv) > 0:
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        print(f"✅ Selesai! Total data: {len(df)} candle.")
        return df
    else:
        return pd.DataFrame()