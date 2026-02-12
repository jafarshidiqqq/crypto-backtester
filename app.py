import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import traceback
from dotenv import load_dotenv
from openai import OpenAI
from engine.data_loader import get_binance_data
from engine.backtester import run_backtest

# --- IMPORT STRATEGI ---
from strategies import simple_ma, bb_rsi, smc, trend_ema, supertrend

# --- LOAD ENV ---
load_dotenv()

# --- 1. CONFIG ---
st.set_page_config(page_title="Crypto Backtester + AI", layout="wide")
st.title("📈 Binance Backtester + DeepSeek Chat 🤖")

# --- 2. SESSION STATE ---
if "backtest_result" not in st.session_state:
    st.session_state.backtest_result = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. SIDEBAR ---
st.sidebar.header("Pengaturan")
symbol = st.sidebar.text_input("Simbol", value="BTC/USDT")
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d", "1w", "1M"], index=1)
start_date = st.sidebar.date_input("Mulai", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("Selesai", pd.to_datetime("today"))

strategy_option = st.sidebar.selectbox(
    "Strategi",
    ("Bollinger Bands + RSI", "Supertrend (Trend Follower)", "Triple EMA Trend", "Smart Money Concept (SMC)", "Simple MA Crossover")
)

st.sidebar.subheader("Manajemen Risiko")
use_sl = st.sidebar.checkbox("Stop Loss (SL)", value=True)
sl_input = st.sidebar.number_input("SL %", 0.1, 5.0, 2.0) if use_sl else 0 
use_tp = st.sidebar.checkbox("Take Profit (TP)", value=True)
tp_input = st.sidebar.number_input("TP %", 0.1, 20.0, 10.0) if use_tp else 0 

# API KEY INPUT
st.sidebar.markdown("---")
env_key = os.getenv("DEEPSEEK_API_KEY")
deepseek_api_key = env_key if env_key else st.sidebar.text_input("DeepSeek API Key", type="password")

run_btn = st.sidebar.button("Jalankan Backtest 🚀", type="primary")

# --- 4. FUNGSI AI CONTEXT ---
def prepare_ai_context(results, strategy, symbol, tf):
    """Merangkum data backtest jadi teks buat AI"""
    log = results.get('trade_log', pd.DataFrame())
    if log.empty: return "Data kosong, tidak ada trade."
    
    # Statistik Tambahan
    win_streak = 0
    loss_streak = 0
    current_streak = 0
    is_win = False
    
    # Hitung Streak Sederhana
    for pnl in log['Profit/Loss %']:
        if pnl > 0:
            if not is_win: current_streak = 0
            is_win = True
            current_streak += 1
            win_streak = max(win_streak, current_streak)
        else:
            if is_win: current_streak = 0
            is_win = False
            current_streak += 1
            loss_streak = max(loss_streak, current_streak)

    summary = f"""
    HASIL BACKTEST:
    - Aset: {symbol} ({tf})
    - Strategi: {strategy}
    - Total Return: {results['total_return_pct']:.2f}%
    - Win Rate: {results['win_rate']:.2f}%
    - Max Drawdown: {results['max_drawdown_pct']:.2f}%
    - Total Trades: {len(log)}
    - Max Win Streak: {win_streak}
    - Max Loss Streak: {loss_streak}
    
    5 TRADE TERAKHIR:
    {log.tail(5).to_string(index=False)}
    """
    return summary

# --- 5. LOGIKA UTAMA ---
if run_btn:
    st.session_state.messages = [] # Reset chat setiap backtest baru
    status = st.status("Memproses...", expanded=True)
    
    try:
        # A. LOAD DATA
        status.write("1️⃣ Mengambil data dari Binance...")
        start_str = f"{start_date} 00:00:00"
        df = get_binance_data(symbol, timeframe, start_str)
        
        if df.empty:
            status.update(label="❌ Gagal ambil data", state="error")
            st.error("Cek koneksi atau simbol aset.")
        else:
            # B. FILTER & STRATEGI
            mask = (df.index <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
            df_filtered = df.loc[mask]
            
            status.write(f"2️⃣ Menerapkan strategi {strategy_option}...")
            if strategy_option == "Simple MA Crossover": df_s = simple_ma.apply_strategy(df_filtered)
            elif strategy_option == "Bollinger Bands + RSI": df_s = bb_rsi.apply_strategy(df_filtered)
            elif strategy_option == "Smart Money Concept (SMC)": df_s = smc.apply_strategy(df_filtered)
            elif strategy_option == "Triple EMA Trend (High Win Rate)": df_s = trend_ema.apply_strategy(df_filtered)
            elif strategy_option == "Supertrend (Trend Follower)": df_s = supertrend.apply_strategy(df_filtered)
            
            # C. RUN BACKTEST
            status.write("3️⃣ Menghitung Profit/Loss...")
            sl_dec = sl_input / 100 if use_sl else 0
            tp_dec = tp_input / 100 if use_tp else 0
            results = run_backtest(df_s, sl_pct=sl_dec, tp_pct=tp_dec)
            
            # D. SIMPAN SESSION & PREPARE AI
            st.session_state.backtest_result = {
                'results': results,
                'df': df_s,
                'log': results.get('trade_log', pd.DataFrame())
            }
            
            # Inject Context ke AI (System Prompt)
            context_data = prepare_ai_context(results, strategy_option, symbol, timeframe)
            system_prompt = f"""
            Anda adalah Trading Mentor pro. Tugas anda menganalisis hasil backtest user.
            Data Backtest User:
            {context_data}
            
            Gaya Bicara: Santai tapi tajam, gunakan Bahasa Indonesia.
            Fokus: Berikan kritik pada Drawdown dan saran optimasi setting.
            """
            st.session_state.messages.append({"role": "system", "content": system_prompt})
            st.session_state.messages.append({"role": "assistant", "content": "Analisis selesai! Data sudah saya baca. Ada yang mau ditanyakan soal hasil ini?"})
            
            status.update(label="✅ Selesai!", state="complete", expanded=False)

    except Exception as e:
        status.update(label="❌ Error", state="error")
        st.error(f"Terjadi kesalahan: {str(e)}")
        st.code(traceback.format_exc())

# --- 6. DISPLAY DASHBOARD ---
if st.session_state.backtest_result:
    data = st.session_state.backtest_result
    res = data['results']
    log = data['log']
    
    # METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Return", f"{res['total_return_pct']:.2f}%", delta_color="normal")
    c2.metric("Win Rate", f"{res['win_rate']:.2f}%")
    c3.metric("Drawdown", f"{res['max_drawdown_pct']:.2f}%")
    c4.metric("Trades", len(log))
    
    # CHART
    st.subheader("Grafik Equity")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=res['dataframe'].index, y=res['dataframe']['Equity_Curve'], mode='lines', line=dict(color='#00FF00')))
    fig.update_layout(height=350, template="plotly_dark", margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 7. CHAT AREA (DEEPSEEK) ---
    st.markdown("---")
    st.subheader("💬 Diskusi dengan AI (DeepSeek)")
    
    if not deepseek_api_key:
        st.warning("⚠️ Masukkan API Key DeepSeek di Sidebar untuk chat.")
    else:
        # Tampilkan History
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # Input User
        if prompt := st.chat_input("Tanya tentang strategi ini..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Response AI
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                try:
                    client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
                    stream = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                        stream=True
                    )
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"AI Error: {str(e)}")

    # LOG EXPANDER
    with st.expander("Lihat Detail Transaksi"):
        st.dataframe(log)
