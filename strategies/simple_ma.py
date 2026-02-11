import pandas as pd

def apply_strategy(df):
    """
    Strategi: Golden Cross
    Beli jika MA 50 > MA 200 via Close Price.
    """
    # Jangan ubah data asli, buat copy
    df = df.copy()
    
    # 1. Hitung Indikator
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # 2. Buat Sinyal
    # 1 = Beli/Tahan, 0 = Jual/Cash
    df['Signal'] = 0 
    df.loc[df['SMA_50'] > df['SMA_200'], 'Signal'] = 1
    
    return df