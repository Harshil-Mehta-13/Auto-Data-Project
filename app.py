# app.py
# Streamlit Stock Dashboard — TradingView/Zerodha‑style (free data)
# Features:
# - Watchlist search with real‑time quotes
# - Candlestick + Volume charts (daily/intraday) with SMA/EMA/RSI/MACD
# - Portfolio upload via Excel (Ticker, Avg_Buy_Price, Quantity)
# - Portfolio P&L table + allocation pie + key summary metrics
# - Company fundamentals summary + latest news (from yfinance)
# - Auto‑refresh control
#
# Data source: Yahoo Finance via yfinance (no API key). Intraday depends on Yahoo limits.
# Note: NSE tickers must end with .NS (e.g., RELIANCE.NS, TCS.NS, INFY.NS)

import io
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ------------------------------
# Helpers
# ------------------------------

def fmt_currency(x: float, symbol: str = "₹"):
    if pd.isna(x):
        return "—"
    try:
        return f"{symbol}{x:,.2f}"
    except Exception:
        return str(x)

@st.cache_data(show_spinner=False)
def fetch_price_history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False)
    # Ensure expected columns
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={c: c.capitalize() for c in df.columns})
    return df

@st.cache_data(show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.fast_info if hasattr(t, "fast_info") else {}
    price = None
    try:
        price = float(info.get("last_price", np.nan))
    except Exception:
        # fallback to history
        hist = t.history(period="1d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
    return {
        "price": price,
        "currency": info.get("currency", "INR"),
        "day_high": info.get("day_high"),
        "day_low": info.get("day_low"),
        "year_high": info.get("year_high"),
        "year_low": info.get("year_low"),
        "market_cap": info.get("market_cap"),
        "exchange": info.get("exchange", ""),
    }

@st.cache_data(show_spinner=False)
def fetch_news(ticker: str) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        if not news:
            return pd.DataFrame()
        rows = []
        for n in news:
            rows.append({
                "title": n.get("title"),
                "publisher": n.get("publisher"),
                "link": n.get("link"),
                "providerPublishTime": pd.to_datetime(n.get("providerPublishTime", 0), unit="s"),
            })
        df = pd.DataFrame(rows).sort_values("providerPublishTime", ascending=False)
        return df
    except Exception:
        return pd.DataFrame()

# --- Technical Indicators (no external TA lib)

def SMA(series: pd.Series, window: int):
    return series.rolling(window).mean()

def EMA(series: pd.Series, span: int):
    return series.ewm(span=span, adjust=False).mean()

def RSI(series: pd.Series, period: int = 14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain, index=series.index).rolling(period).mean()
    roll_down = pd.Series(loss, index=series.index).rolling(period).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi

def MACD(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = EMA(series, fast)
    ema_slow = EMA(series, slow)
    macd = ema_fast - ema_slow
    signal_line = EMA(macd, signal)
    hist = macd - signal_line
    return macd, signal_line, hist

# ------------------------------
# UI Config
# ------------------------------

st.set_page_config(
    page_title="Stock Dashboard (TradingView‑style)",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("⚙️ Controls")

# Auto refresh
refresh_sec = st.sidebar.number_input("Auto‑refresh (seconds)", min_value=0, max_value=300, value=0, help="Set to 0 to disable auto refresh")
if refresh_sec and refresh_sec > 0:
    st.experimental_singleton.clear()  # ensure no singleton cache
    st.experimental_rerun  # reference to avoid linter
    st.autorefresh(interval=refresh_sec * 1000, key="autorefresh")

# Theme toggles
show_ma = st.sidebar.multiselect("Moving Averages", options=["SMA20", "SMA50", "SMA200", "EMA20", "EMA50"], default=["SMA20", "SMA50"])
show_rsi = st.sidebar.checkbox("Show RSI (14)", value=True)
show_macd = st.sidebar.checkbox("Show MACD (12,26,9)", value=False)

# Default popular tickers (NSE add .NS)
popular = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "TATASTEEL.NS", "AAPL", "MSFT", "NVDA"]

st.title("🧭 Stock Dashboard — TradingView‑style (Free Data)")

# Tabs
tab_watch, tab_chart, tab_portfolio, tab_news = st.tabs(["🔎 Watchlist", "📈 Charts", "💼 Portfolio", "📰 News & Fundamentals"]) 

# ---------------------------------
# Watchlist
# ---------------------------------
with tab_watch:
    c1, c2 = st.columns([2,1])
    with c1:
        query = st.text_input("Search ticker (e.g., RELIANCE.NS, TCS.NS, AAPL)", value=popular[0])
    with c2:
        st.write("Popular:")
        st.write(", ".join(popular))

    if query:
        q = fetch_quote(query)
        if q.get("price") is None:
            st.error("Could not fetch quote. Check the ticker symbol (remember .NS for NSE).")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Last Price", fmt_currency(q["price"], symbol="₹" if q.get("currency","INR")=="INR" else "$"))
            m2.metric("Day Low / High", f"{fmt_currency(q['day_low'])} – {fmt_currency(q['day_high'])}")
            m3.metric("52W Low / High", f"{fmt_currency(q['year_low'])} – {fmt_currency(q['year_high'])}")
            mc = q.get("market_cap")
            m4.metric("Mkt Cap", f"{mc/1e12:.2f} T" if mc and mc>1e12 else (f"{mc/1e9:.2f} B" if mc and mc>1e9 else (f"{mc/1e6:.2f} M" if mc and mc>1e6 else "—")))

# ---------------------------------
# Charts
# ---------------------------------
with tab_chart:
    c1, c2, c3, c4 = st.columns([2,1,1,1])
    ticker = c1.text_input("Ticker", value=popular[0], key="chart_ticker")
    period = c2.selectbox("Period", ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"], index=4)
    interval = c3.selectbox("Interval", ["1m","2m","5m","15m","30m","60m","90m","1h","1d","5d","1wk","1mo","3mo"], index=8)
    chart_type = c4.selectbox("Chart", ["Candlestick","Line"], index=0)

    df = fetch_price_history(ticker, period=period, interval=interval)

    if df.empty:
        st.warning("No data for this combination. Try a longer period or daily interval.")
    else:
        # Indicators
        close = df["Close"].copy()
        overlays = {}
        if "SMA20" in show_ma:
            overlays["SMA20"] = SMA(close, 20)
        if "SMA50" in show_ma:
            overlays["SMA50"] = SMA(close, 50)
        if "SMA200" in show_ma:
            overlays["SMA200"] = SMA(close, 200)
        if "EMA20" in show_ma:
            overlays["EMA20"] = EMA(close, 20)
        if "EMA50" in show_ma:
            overlays["EMA50"] = EMA(close, 50)

        macd_line = signal_line = macd_hist = None
        rsi = None
        if show_macd:
            macd_line, signal_line, macd_hist = MACD(close)
        if show_rsi:
            rsi = RSI(close, 14)

        # Build figure with volume + optional RSI/MACD as subplots
        rows = 2 + (1 if show_rsi else 0) + (1 if show_macd else 0)
        specs = [[{"secondary_y": False}], [{"secondary_y": True}]]
        if show_rsi:
            specs.append([{"secondary_y": False}])
        if show_macd:
            specs.append([{"secondary_y": False}])

        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, specs=specs)

        # Price
        if chart_type == "Candlestick":
            fig.add_trace(
                go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"),
                row=1, col=1
            )
        else:
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Close"), row=1, col=1)

        # Overlays
        for name, series in overlays.items():
            fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=name), row=1, col=1)

        # Volume
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", opacity=0.4), row=2, col=1)

        # RSI
        next_row = 3
        if show_rsi:
            fig.add_trace(go.Scatter(x=rsi.index, y=rsi, mode="lines", name="RSI(14)"), row=next_row, col=1)
            fig.add_hline(y=70, line_dash="dot", row=next_row, col=1)
            fig.add_hline(y=30, line_dash="dot", row=next_row, col=1)
            next_row += 1

        # MACD
        if show_macd:
            fig.add_trace(go.Scatter(x=macd_line.index, y=macd_line, name="MACD"), row=next_row, col=1)
            fig.add_trace(go.Scatter(x=signal_line.index, y=signal_line, name="Signal"), row=next_row, col=1)
            fig.add_trace(go.Bar(x=macd_hist.index, y=macd_hist, name="Hist", opacity=0.5), row=next_row, col=1)

        fig.update_layout(height=700, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis_rangeslider_visible=(chart_type=="Candlestick" and interval in ["1d","5d","1wk","1mo","3mo"]))
        st.plotly_chart(fig, use_container_width=True, theme="streamlit")

# ---------------------------------
# Portfolio
# ---------------------------------
with tab_portfolio:
    st.subheader("Upload Portfolio Excel")
    st.caption("Columns required: Ticker, Avg_Buy_Price, Quantity. Example: RELIANCE.NS, 2500, 10")

    # Downloadable template
    sample = pd.DataFrame({
        "Ticker": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
        "Avg_Buy_Price": [2500, 3300, 1500],
        "Quantity": [10, 5, 12],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        sample.to_excel(writer, index=False, sheet_name="Portfolio")
    st.download_button(
        label="Download Excel Template",
        data=buf.getvalue(),
        file_name="portfolio_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Drop your Excel here", type=["xlsx"])

    if uploaded:
        try:
            pf = pd.read_excel(uploaded)
            required = {"Ticker", "Avg_Buy_Price", "Quantity"}
            if not required.issubset(set(pf.columns)):
                st.error("Excel must have columns: Ticker, Avg_Buy_Price, Quantity")
            else:
                # Fetch current prices for unique tickers
                tickers = [t for t in pf["Ticker"].astype(str).unique().tolist() if t]
                quotes = {}
                for t in tickers:
                    q = fetch_quote(t)
                    quotes[t] = q.get("price", np.nan)

                rows = []
                for _, r in pf.iterrows():
                    t = str(r["Ticker"]) 
                    avg = float(r["Avg_Buy_Price"]) 
                    qty = float(r["Quantity"]) 
                    cur = quotes.get(t, np.nan)
                    invest = avg * qty
                    cur_val = (cur if not pd.isna(cur) else 0.0) * qty
                    pl = cur_val - invest
                    ret = (pl / invest * 100.0) if invest else np.nan
                    rows.append({
                        "Ticker": t,
                        "Avg Price": avg,
                        "Qty": qty,
                        "Current Price": cur,
                        "Investment": invest,
                        "Current Value": cur_val,
                        "P/L": pl,
                        "Return %": ret,
                    })
                out = pd.DataFrame(rows)

                # Summary
                total_invest = out["Investment"].sum()
                total_value = out["Current Value"].sum()
                total_pl = out["P/L"].sum()
                total_ret = (total_pl / total_invest * 100.0) if total_invest else np.nan

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Investment", fmt_currency(total_invest))
                k2.metric("Current Value", fmt_currency(total_value))
                k3.metric("Total P/L", fmt_currency(total_pl))
                k4.metric("Return %", f"{total_ret:.2f}%" if not pd.isna(total_ret) else "—")

                st.dataframe(out.style.format({
                    "Avg Price": "{:.2f}",
                    "Qty": "{:.2f}",
                    "Current Price": "{:.2f}",
                    "Investment": "{:.2f}",
                    "Current Value": "{:.2f}",
                    "P/L": "{:.2f}",
                    "Return %": "{:.2f}",
                }), use_container_width=True)

                # Allocation Pie
                alloc = out.groupby("Ticker")["Current Value"].sum().sort_values(ascending=False)
                if not alloc.empty and alloc.sum() > 0:
                    fig_alloc = go.Figure(data=[go.Pie(labels=alloc.index, values=alloc.values, hole=0.5)])
                    fig_alloc.update_layout(title="Allocation by Current Value")
                    st.plotly_chart(fig_alloc, use_container_width=True)

        except Exception as e:
            st.exception(e)

# ---------------------------------
# News & Fundamentals
# ---------------------------------
with tab_news:
    t1, t2 = st.columns([2,1])
    news_ticker = t1.text_input("Ticker for news & fundamentals", value=popular[0], key="news_ticker")
    show_info = t2.checkbox("Show fundamentals", value=True)

    if news_ticker:
        if show_info:
            tk = yf.Ticker(news_ticker)
            fi = getattr(tk, "fast_info", {}) or {}
            inf = tk.get_info() if hasattr(tk, "get_info") else {}

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Currency", fi.get("currency", inf.get("currency","—")))
            c2.metric("Exchange", fi.get("exchange","—"))
            c3.metric("PEG", f"{inf.get('pegRatio','—')}")
            c4.metric("P/E", f"{inf.get('trailingPE','—')}")

            st.write("**Business Summary**")
            desc = inf.get("longBusinessSummary") or inf.get("longName") or "—"
            st.write(desc)

        st.subheader("Latest News")
        news_df = fetch_news(news_ticker)
        if news_df.empty:
            st.info("No news available from source right now.")
        else:
            for _, n in news_df.head(15).iterrows():
                st.markdown(f"- [{n['title']}]({n['link']})  ")
                st.caption(f"{n['publisher']} • {n['providerPublishTime']}")

# ------------------------------
# Footer
# ------------------------------
st.caption("Data from Yahoo Finance via yfinance. This app is for education only — not financial advice.")
