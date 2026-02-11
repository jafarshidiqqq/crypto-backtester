import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from openai import OpenAI
from engine.data_loader import get_binance_data
from engine.backtester import run_backtest

# --- IMPORT STRATEGI ---
from strategies import simple_ma, bb_rsi, smc, trend_ema, supertrend

# --- LOAD ENV ---
load_dotenv()

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Crypto Backtester Pro + AI Chat", layout="wide")
st.title("📈 Crypto Backtester + DeepSeek Chat 💬")

# --- 2. SESSION STATE (PENTING AGAR CHAT TIDAK HILANG) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "backtest_data" not in st.session_state:
    st.session_state.backtest_data = None

# --- 3. SIDEBAR ---
st.sidebar.header("Pengaturan Backtest")
symbol = st.sidebar.text_input("Simbol Aset", value="BTC/USDT")
timeframe = st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d", "1w", "1M"], index=1)

default_start = "2020-01-01" if timeframe in ["1w", "1M"] else "2023-01-01"
start_date = st.sidebar.date_input("Mulai", pd.to_datetime(default_start))
end_date = st.sidebar.date_input("Selesai", pd.to_datetime("today"))

strategy_option = st.sidebar.selectbox(
    "Pilih Strategi",
    (
        "Supertrend (Trend Follower)",      
        "Triple EMA Trend (High Win Rate)",
        "Bollinger Bands + RSI", 
        "Smart Money Concept (SMC)",
        "Simple MA Crossover"
    )
)

st.sidebar.subheader("Manajemen Risiko")
use_sl = st.sidebar.checkbox("Aktifkan Stop Loss (SL)", value=True)
sl_input = st.sidebar.number_input("Stop Loss (%)", min_value=0.1, value=2.0, step=0.1) if use_sl else 0 
use_tp = st.sidebar.checkbox("Aktifkan Take Profit (TP)", value=True)
tp_input = st.sidebar.number_input("Take Profit (%)", min_value=0.1, value=10.0, step=0.1) if use_tp else 0 

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Pengaturan AI")
env_api_key = os.getenv("DEEPSEEK_API_KEY")
if env_api_key:
    deepseek_api_key = env_api_key
    st.sidebar.success("✅ API Key dari .env")
else:
    deepseek_api_key = st.sidebar.text_input("DeepSeek API Key", type="password", placeholder="sk-...")

run_btn = st.sidebar.button("Jalankan Backtest 🚀", type="primary")

# --- 4. FUNGSI PREPARE DATA UNTUK AI ---
def prepare_ai_context(results, strategy_name, symbol, timeframe, sl, tp):
    """
    Menyiapkan data super lengkap untuk DeepSeek agar analisisnya tajam.
    """
    df = results['dataframe']
    log = results.get('trade_log', pd.DataFrame())
    
    if log.empty:
        return "Tidak ada transaksi yang terjadi."

    # Statistik Tambahan
    best_trade = log['Profit/Loss %'].max()
    worst_trade = log['Profit/Loss %'].min()
    avg_trade = log['Profit/Loss %'].mean()
    
    # Hitung Consecutive Loss (Kekalahan Beruntun)
    # Ini penting untuk psikologi trader
    loss_streak = 0
    max_loss_streak = 0
    current_streak = 0
    
    for pnl in log['Profit/Loss %']:
        if pnl < 0:
            current_streak += 1
        else:
            max_loss_streak = max(max_loss_streak, current_streak)
            current_streak = 0
    max_loss_streak = max(max_loss_streak, current_streak) # Cek terakhir

    # Ambil 30 Trade Terakhir (String Format)
    recent_trades = log.tail(30).to_string(index=False)

    context = f"""
    DATA BACKTEST LENGKAP:
    - Aset: {symbol} ({timeframe})
    - Strategi: {strategy_name}
    - Setting: SL {sl}%, TP {tp}%
    
    PERFORMA UTAMA:
    - Total Return: {results['total_return_pct']:.2f}%
    - Win Rate: {results['win_rate']:.2f}%
    - Max Drawdown: {results['max_drawdown_pct']:.2f}%
    - Total Trades: {len(log)}
    
    STATISTIK MENDALAM:
    - Rata-rata Profit per Trade: {avg_trade:.2f}%
    - Best Trade: {best_trade:.2f}%
    - Worst Trade: {worst_trade:.2f}%
    - Max Consecutive Loss (Kalah Beruntun): {max_loss_streak} kali
    
    30 TRANSAKSI TERAKHIR:
    {recent_trades}
    """
    return context

# --- 5. LOGIKA BACKTEST ---
if run_btn:
    with st.spinner('Sedang menghitung...'):
        start_date_str = f"{start_date} 00:00:00"
        df = get_binance_data(symbol, timeframe, start_date=start_date_str)
        
        if not df.empty:
            mask = (df.index <= pd.to_datetime(end_date) + pd.Timedelta(days=1))
            df_filtered = df.loc[mask]
            
            # Apply Strategy
            if strategy_option == "Simple MA Crossover": df_s = simple_ma.apply_strategy(df_filtered)
            elif strategy_option == "Bollinger Bands + RSI": df_s = bb_rsi.apply_strategy(df_filtered)
            elif strategy_option == "Smart Money Concept (SMC)": df_s = smc.apply_strategy(df_filtered)
            elif strategy_option == "Triple EMA Trend (High Win Rate)": df_s = trend_ema.apply_strategy(df_filtered)
            elif strategy_option == "Supertrend (Trend Follower)": df_s = supertrend.apply_strategy(df_filtered)
            
            # Run Backtest
            sl_dec = sl_input / 100 if use_sl else 0
            tp_dec = tp_input / 100 if use_tp else 0
            results = run_backtest(df_s, sl_pct=sl_dec, tp_pct=tp_dec)
            
            # SIMPAN HASIL KE SESSION STATE (Agar tidak hilang saat chat)
            st.session_state.backtest_data = {
                'results': results,
                'df': df_s,
                'log': results.get('trade_log', pd.DataFrame())
            }
            
            # RESET CHAT HISTORY SAAT BACKTEST BARU
            st.session_state.messages = []
            
            # PREPARE SYSTEM PROMPT UNTUK AI
            context_data = prepare_ai_context(results, strategy_option, symbol, timeframe, sl_input, tp_input)
            
            system_prompt = f"""
            Anda adalah Senior Quantitative Analyst & Trading Mentor.
            Tugas Anda adalah menganalisis data backtest user dan memberikan insight kritis.
            
            Data yang tersedia:
            {context_data}
            
            Panduan Gaya Bicara:
            - Jujur dan tajam. Jika strateginya jelek, katakan jelek.
            - Fokus pada "Risk to Reward" dan "Drawdown".
            - Berikan saran konkret (angka/setting) untuk perbaikan.
            - Gunakan Bahasa Indonesia yang profesional namun santai.
            - Gunakan format Markdown (Bold, List) agar mudah dibaca.
            """
            
            # Masukkan System Prompt ke memory chat (Hidden dari user)
            st.session_state.messages.append({"role": "system", "content": system_prompt})
            
            # Pesan Pembuka AI
            st.session_state.messages.append({"role": "assistant", "content": "Halo! Saya sudah membaca data backtest Anda. Apa yang ingin Anda diskusikan? Lihat saran pertanyaan di bawah 👇"})

# --- 6. DISPLAY HASIL (DARI SESSION STATE) ---
if st.session_state.backtest_data:
    data = st.session_state.backtest_data
    res = data['results']
    log = data['log']
    
    # A. METRIK
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Return", f"{res['total_return_pct']:.2f}%", delta=f"{res['total_return_pct']:.2f}%")
    col2.metric("Max Drawdown", f"{res['max_drawdown_pct']:.2f}%")
    col3.metric("Win Rate", f"{res['win_rate']:.2f}%")
    col4.metric("Total Trades", len(log))

    # B. GRAFIK EQUITY
    st.subheader("Pertumbuhan Modal")
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=res['dataframe'].index, y=res['dataframe']['Equity_Curve'], mode='lines', line=dict(color='#00ff00')))
    fig_eq.update_layout(height=300, template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_eq, use_container_width=True)

    # C. AREA CHAT AI (DEEPSEEK)
    st.markdown("---")
    st.header("💬 Diskusi dengan AI (DeepSeek)")

    # Peringatan jika API Key kosong
    if not deepseek_api_key:
        st.warning("⚠️ Masukkan API Key DeepSeek untuk mulai chatting.")
    else:
        # 1. Tampilkan History Chat
        for msg in st.session_state.messages:
            if msg["role"] != "system": # Jangan tampilkan system prompt
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 2. Saran Pertanyaan (Tombol Cepat)
        st.write("Saran Pertanyaan:")
        col_q1, col_q2, col_q3 = st.columns(3)
        user_input = None
        
        if col_q1.button("🔍 Analisis Kelemahan Strategi"):
            user_input = "Analisis kelemahan terbesar strategi ini berdasarkan data trade log. Kenapa drawdown bisa terjadi?"
        if col_q2.button("🛠️ Saran Optimasi Setting"):
            user_input = "Berikan 3 saran konkret untuk mengubah setting (Timeframe/SL/TP) agar Win Rate naik."
        if col_q3.button("📉 Bahas Drawdown/Loss"):
            user_input = "Lihat loss streak saya. Apakah strategi ini aman untuk psikologi trader pemula?"

        # 3. Input Chat Manual
        chat_input = st.chat_input("Ketik pertanyaan Anda di sini...")
        if chat_input:
            user_input = chat_input

        # 4. Proses Respon AI
        if user_input:
            # Tampilkan pesan user
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Panggil API DeepSeek
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                try:
                    client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
                    
                    # Stream response biar keren
                    stream = client.chat.completions.create(
                        model="deepseek-chat", # Pastikan model name benar
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages
                        ],
                        stream=True
                    )
                    
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    
                    # Simpan respon AI ke history
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    message_placeholder.error(error_msg)
                    if "401" in str(e):
                        st.error("Kunci API salah. Cek .env atau input manual.")
                    elif "insufficient_quota" in str(e):
                        st.error("Saldo API DeepSeek habis.")

    # D. DATA LOG (Di Bawah Chat)
    with st.expander("📜 Lihat Detail Trade Log"):
        if not log.empty:
            st.dataframe(log.style.applymap(lambda x: 'color: #4CAF50' if x > 0 else ('color: #FF5252' if x < 0 else ''), subset=['Profit/Loss %']))
else:
    st.info("👈 Tekan tombol 'Jalankan Backtest' di sidebar untuk memulai.")