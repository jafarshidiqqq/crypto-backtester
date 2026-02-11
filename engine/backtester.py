import pandas as pd
import numpy as np

def run_backtest(df, initial_capital=1000, sl_pct=0.0, tp_pct=0.0):
    """
    Backtest engine update: Menghitung Win Rate.
    """
    df = df.copy()
    
    position = 0 # 0: Cash, 1: Long
    entry_price = 0
    entry_date = None
    
    equity = [initial_capital]
    trade_log = [] 
    
    for i in range(1, len(df)):
        current_date = df.index[i]
        current_price = df['Close'].iloc[i]
        prev_signal = df['Signal'].iloc[i-1] 
        
        action_taken = False 
        
        # 1. CEK EXIT (JUAL)
        if position == 1:
            pnl_pct = (current_price - entry_price) / entry_price
            exit_reason = ""
            exit_price = current_price
            
            # Cek Stop Loss
            if sl_pct > 0 and pnl_pct <= -sl_pct:
                exit_price = entry_price * (1 - sl_pct)
                exit_reason = "Stop Loss (SL)"
                action_taken = True
                
            # Cek Take Profit
            elif tp_pct > 0 and pnl_pct >= tp_pct:
                exit_price = entry_price * (1 + tp_pct)
                exit_reason = "Take Profit (TP)"
                action_taken = True
                
            # Cek Sinyal Jual Strategi
            elif prev_signal == 0:
                exit_price = current_price
                exit_reason = "Signal Sell (Strategy)"
                action_taken = True
            
            # EKSEKUSI JUAL
            if action_taken:
                position = 0
                actual_return = (exit_price - entry_price) / entry_price
                current_equity = equity[-1] * (1 + actual_return)
                equity.append(current_equity)
                
                trade_log.append({
                    'Tanggal': current_date,
                    'Tipe': 'SELL',
                    'Harga': exit_price,
                    'Alasan': exit_reason,
                    'Profit/Loss %': round(actual_return * 100, 2),
                    'Saldo Akhir': round(current_equity, 2)
                })
                continue 

        # 2. CEK ENTRY (BELI)
        if position == 0 and prev_signal == 1:
            position = 1
            entry_price = current_price
            entry_date = current_date
            equity.append(equity[-1]) 
            
            trade_log.append({
                'Tanggal': current_date,
                'Tipe': 'BUY',
                'Harga': entry_price,
                'Alasan': 'Signal Buy (Strategy)',
                'Profit/Loss %': 0.0,
                'Saldo Akhir': round(equity[-1], 2)
            })
            action_taken = True

        # 3. HOLD
        if not action_taken:
            if position == 1:
                daily_change = (current_price - df['Close'].iloc[i-1]) / df['Close'].iloc[i-1]
                equity.append(equity[-1] * (1 + daily_change))
            else:
                equity.append(equity[-1])

    # Rapikan Data
    if len(equity) > len(df): equity = equity[1:]
    df['Equity_Curve'] = equity
    
    running_max = df['Equity_Curve'].cummax()
    df['Drawdown'] = (df['Equity_Curve'] - running_max) / running_max
    
    total_return = (df['Equity_Curve'].iloc[-1] / initial_capital) - 1
    max_drawdown = df['Drawdown'].min()
    
    # --- HITUNG WIN RATE (BARU) ---
    # Kita hanya menghitung transaksi SELL (yang sudah realisasi untung/rugi)
    # Transaksi BUY belum dihitung karena belum selesai
    closed_trades = [t for t in trade_log if t['Tipe'] == 'SELL']
    total_trades = len(closed_trades)
    winning_trades = len([t for t in closed_trades if t['Profit/Loss %'] > 0])
    
    if total_trades > 0:
        win_rate = (winning_trades / total_trades) * 100
    else:
        win_rate = 0.0
    
    return {
        "total_return_pct": total_return * 100,
        "max_drawdown_pct": max_drawdown * 100,
        "win_rate": win_rate, # <--- Dikirim ke app.py
        "equity_curve": df['Equity_Curve'],
        "dataframe": df,
        "trade_log": pd.DataFrame(trade_log)
    }