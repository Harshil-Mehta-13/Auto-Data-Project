# app.py
import io
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import requests
from bs4 import BeautifulSoup

# -------------------------
# Helpers / Data fetchers
# -------------------------
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

@st.cache_data(ttl=60 * 60 * 24)  # refresh daily
def get_nifty500_tickers():
    """
    Try NSE official CSV first, fallback to Wikipedia parsing, then to a small builtin list.
    Returns list of tickers *with* .NS suffix (for yfinance).
    """
    # 1) official CSV
    csv_url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        resp = requests.get(csv_url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        # common column name 'Symbol'
        if any(col.lower() == "symbol" for col in df.columns):
            # Find 'Symbol' case-insensitively
            sym_col = next(c for c in df.columns if c.lower() == "symbol")
            syms = df[sym_col].dropna().astype(str).str.strip().tolist()
            syms = [s + ("" if s.endswith(".NS") else ".NS") for s in syms if s]
            if syms:
                return syms
    except Exception:
        # ignore and fallback
        pass

    # 2) Try Wikipedia table (less official but often works)
    try:
        wiki = "https://en.wikipedia.org/wiki/NIFTY_500"
        tables = pd.read_html(wiki)
        if tables:
            # pick the largest table (most rows)
            df = max(tables, key=lambda t: t.shape[0])
            cols = [str(c).strip().lower() for c in df.columns]
            # look for likely column
            for candidate in ("symbol", "ticker", "ticker symbol", "code", "scrip"):
                if candidate in cols:
                    sym_col = df.columns[cols.index(candidate)]
                    syms = df[sym_col].dropna().astype(str).str.strip().tolist()
                    syms = [s + ("" if s.endswith(".NS") else ".NS") for s in syms if s]
                    if syms:
                        return syms
    except Exception:
        pass

    # 3) fallback small list
    fallback = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"
    ]
    return fallback


@st.cache_data(ttl=60 * 5)
def fetch_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Download price history, normalize columns, return dataframe with standard OHLCV columns."""
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, threads=False)
        # sometimes empty or MultiIndex columns — normalize
        if df is None or df.empty:
            # try ticker.history fallback
            t = yf.Ticker(symbol)
            df = t.history(period=period, interval=interval)
            if df is None or df.empty:
                return pd.DataFrame()
        # flatten multiindex columns if any
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join([str(x) for x in col if x is not None]).strip() for col in df.columns.values]
        # normalize names to standard ones
        cols_map = {}
        for c in df.columns:
            cl = str(c).lower()
            if "open" in cl and "adj" not in cl:
                cols_map[c] = "Open"
            elif "high" in cl:
                cols_map[c] = "High"
            elif "low" in cl and "adj" not in cl:
                cols_map[c] = "Low"
            elif "adj" in cl and "close" in cl:
                cols_map[c] = "Adj Close"
            elif "close" in cl:
                cols_map[c] = "Close"
            elif "volume" in cl:
                cols_map[c] = "Volume"
            else:
                cols_map[c] = c
        df = df.rename(columns=cols_map)
        # ensure required columns exist
        for req in ("Open", "High", "Low", "Close"):
            if req not in df.columns:
                return pd.DataFrame()
        df = df.reset_index()
        # ensure datetime index column name 'Date' or 'ts'
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60 * 60)
def fetch_company_info(symbol: str) -> dict:
    """Return Ticker.info with safe fallback."""
    try:
        t = yf.Ticker(symbol)
        info = {}
        try:
            info = t.get_info() if hasattr(t, "get_info") else t.info
        except Exception:
            # older yfinance exposes .info
            info = getattr(t, "info", {}) or {}
        # some quick important fields (safe)
        quick = {
            "shortName": info.get("shortName") or info.get("longName"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "marketCap": info.get("marketCap"),
            "previousClose": info.get("previousClose") or info.get("regularMarketPreviousClose"),
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "priceToBook": info.get("priceToBook"),
            "dividendYield": info.get("dividendYield"),
        }
        info["_scan"] = quick
        return info
    except Exception:
        return {}


@st.cache_data(ttl=60 * 30)
def fetch_news(symbol_short: str):
    """Try yfinance news first, fallback to Google News RSS (India)."""
    try:
        t = yf.Ticker(symbol_short)
        news = getattr(t, "news", None)
        if news:
            # normalize
            out = []
            for n in news:
                out.append({
                    "title": n.get("title"),
                    "link": n.get("link"),
                    "publisher": n.get("publisher"),
                    "time": pd.to_datetime(n.get("providerPublishTime", None), unit="s", errors="coerce")
                })
            return out
    except Exception:
        pass

    # fallback: Google News RSS
    try:
        q = f"{symbol_short} stock India"
        rss = f"https://news.google.com/rss/search?q={requests.utils.requote_uri(q)}&hl=en-IN&gl=IN&ceid=IN:en"
        res = requests.get(rss, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(res.content, "xml")
        items = soup.find_all("item")[:10]
        out = []
        for it in items:
            out.append({
                "title": it.title.text if it.title else None,
                "link": it.link.text if it.link else None,
                "publisher": it.source.text if it.source else None,
                "time": it.pubDate.text if it.pubDate else None
            })
        return out
    except Exception:
        return []


# -------------------------
# Technical calculations
# -------------------------
def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA, EMA, RSI, MACD columns to the dataframe (expects 'Close' column)."""
    d = df.copy()
    if "Close" not in d.columns:
        return d

    close = pd.to_numeric(d["Close"], errors="coerce")
    d["SMA20"] = close.rolling(window=20, min_periods=1).mean()
    d["SMA50"] = close.rolling(window=50, min_periods=1).mean()
    d["SMA200"] = close.rolling(window=200, min_periods=1).mean()
    d["EMA20"] = close.ewm(span=20, adjust=False).mean()
    d["EMA50"] = close.ewm(span=50, adjust=False).mean()

    # RSI (EWMA smoothing)
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(span=14, adjust=False).mean()
    roll_down = down.ewm(span=14, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    d["RSI14"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    d["MACD"] = ema12 - ema26
    d["MACD_signal"] = d["MACD"].ewm(span=9, adjust=False).mean()
    d["MACD_hist"] = d["MACD"] - d["MACD_signal"]

    return d


# -------------------------
# UI & Tabs
# -------------------------
st.set_page_config(page_title="Nifty 500 — Stock Dashboard", layout="wide")
st.title("📈 Nifty 500 Stock Dashboard")

# master dropdown
tickers = get_nifty500_tickers()
st.sidebar.markdown("### Select stock (NIFTY 500)")
# format for user: show without .NS when possible but keep underlying value full
options_display = [t[:-3] if t.endswith(".NS") else t for t in tickers]
selected_display = st.sidebar.selectbox("Ticker", options_display, index=0, format_func=lambda x: x)
# map back to yahoo symbol
if selected_display.endswith(".NS"):
    symbol = selected_display
else:
    symbol = selected_display + ".NS"  # default to NSE
# short symbol without suffix for news/ticker object where needed
symbol_short = symbol.replace(".NS", "")

# tabs
tab_overview, tab_chart, tab_fin, tab_tech, tab_news = st.tabs(
    ["Overview", "Chart", "Financials", "Technicals", "News"]
)

# Overview
with tab_overview:
    st.header(f"{symbol_short} — Overview")
    info = fetch_company_info(symbol)
    quick = info.get("_scan", {}) if isinstance(info, dict) else {}
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Price", f"{quick.get('currentPrice', '—')} {info.get('currency','')}")
    col2.metric("Market Cap", f"{human_readable(quick.get('marketCap')) if quick.get('marketCap') else '—'}")
    col3.metric("P/E (TTM)", quick.get("trailingPE", "—"))
    col4.metric("P/B", quick.get("priceToBook", "—"))
    st.write(info.get("longBusinessSummary") or info.get("longName") or "No business summary available.")

# Chart
with tab_chart:
    st.header(f"{symbol_short} — Candlestick chart")
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        period = st.selectbox("Period", ["1mo","3mo","6mo","1y","2y","5y","max"], index=2)
    with col2:
        interval = st.selectbox("Interval", ["1d","1wk","1mo"], index=0)
    with col3:
        show_sma = st.checkbox("Show SMA20/SMA50", True)
        show_ema = st.checkbox("Show EMA20/EMA50", False)
        show_rsi = st.checkbox("Show RSI(14)", False)
        show_macd = st.checkbox("Show MACD", False)

    df = fetch_price_history(symbol, period=period, interval=interval)
    if df.empty:
        st.warning("No price data available for this period/interval.")
    else:
        df = add_technical_indicators(df)
        # Plotly: candlestick + volume + optional RSI/MACD as subplots
        rows = 2 + (1 if show_rsi else 0) + (1 if show_macd else 0)
        specs = [[{"rowspan":1}], [{"rowspan":1}]]
        # We'll create subplots manually with make_subplots
        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                            vertical_spacing=0.02,
                            row_heights=[0.6, 0.2] + ([0.2] if show_rsi else []) + ([0.2] if show_macd else []))

        # Candlestick row 1
        fig.add_trace(go.Candlestick(
            x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"
        ), row=1, col=1)

        if show_sma and "SMA20" in df.columns:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA20'], name="SMA20", line=dict(width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA50'], name="SMA50", line=dict(width=1)), row=1, col=1)
        if show_ema and "EMA20" in df.columns:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA20'], name="EMA20", line=dict(dash="dot", width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA50'], name="EMA50", line=dict(dash="dot", width=1)), row=1, col=1)

        # Volume in row 2
        fig.add_trace(go.Bar(x=df['Date'], y=df.get('Volume', 0), name="Volume", marker=dict(opacity=0.6)), row=2, col=1)

        cur_row = 3
        if show_rsi:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI14'], name="RSI(14)"), row=cur_row, col=1)
            fig.add_hline(y=70, line_dash="dot", row=cur_row, col=1)
            fig.add_hline(y=30, line_dash="dot", row=cur_row, col=1)
            cur_row += 1
        if show_macd:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], name="MACD"), row=cur_row, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD_signal'], name="MACD Signal"), row=cur_row, col=1)
            fig.add_trace(go.Bar(x=df['Date'], y=df['MACD_hist'], name="MACD Hist"), row=cur_row, col=1)

        fig.update_layout(height=700, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

# Financials
with tab_fin:
    st.header(f"{symbol_short} — Financials (Yahoo)")
    t = yf.Ticker(symbol)
    try:
        fin = t.financials
        bs = t.balance_sheet
        cf = t.cashflow
        if not fin.empty:
            st.subheader("Income Statement")
            st.dataframe(fin)
        if not bs.empty:
            st.subheader("Balance Sheet")
            st.dataframe(bs)
        if not cf.empty:
            st.subheader("Cash Flow")
            st.dataframe(cf)
    except Exception:
        st.info("Financial statements not available for this ticker.")

# Technicals tab
with tab_tech:
    st.header(f"{symbol_short} — Technical Indicators")
    if df.empty:
        st.info("No price data to compute technicals.")
    else:
        last = df.iloc[-1]
        cols = st.columns(4)
        cols[0].metric("Close", f"{last['Close']:.2f}")
        cols[1].metric("SMA20", f"{last.get('SMA20', np.nan):.2f}")
        cols[2].metric("RSI(14)", f"{last.get('RSI14', np.nan):.2f}")
        cols[3].metric("MACD", f"{last.get('MACD', np.nan):.4f}")
        st.subheader("Recent Indicators (table)")
        showcols = [c for c in ["Date", "Close", "SMA20", "SMA50", "EMA20", "EMA50", "RSI14", "MACD", "MACD_signal", "MACD_hist"] if c in df.columns]
        st.dataframe(df[showcols].tail(100), use_container_width=True)

# News
with tab_news:
    st.header(f"{symbol_short} — Latest News")
    news = fetch_news(symbol_short)
    if not news:
        st.info("No news currently available.")
    else:
        for n in news[:20]:
            title = n.get("title") or n.get("title")
            link = n.get("link")
            pub = n.get("time")
            st.markdown(f"- [{title}]({link})  \n  _{pub}_")

# -------------------------
# Utilities
# -------------------------
def human_readable(n):
    try:
        n = float(n)
    except Exception:
        return n
    for unit in ["", "K", "M", "B", "T"]:
        if abs(n) < 1000.0:
            return f"{n:3.2f}{unit}"
        n /= 1000.0
    return f"{n:.2f}P"
