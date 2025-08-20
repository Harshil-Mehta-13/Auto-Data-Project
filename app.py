# app.py
# Streamlit NIFTY-500 stock dashboard
# Requirements (requirements.txt): streamlit, pandas, numpy, yfinance, plotly, requests, beautifulsoup4, lxml, html5lib

import io
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from bs4 import BeautifulSoup

# -------------------------
# Utilities
# -------------------------
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def human_readable(n):
    """Turn large number into a compact string (K/M/B/T)."""
    try:
        n = float(n)
    except Exception:
        return n
    abs_n = abs(n)
    if abs_n < 1_000:
        return f"{n:,.0f}"
    for unit in ["K", "M", "B", "T"]:
        n /= 1000.0
        if abs(n) < 1000.0:
            return f"{n:3.2f}{unit}"
    return f"{n:.2f}P"

# -------------------------
# Data fetchers & processors
# -------------------------
@st.cache_data(ttl=60 * 60 * 24)  # refresh daily
def get_nifty500_tickers():
    """
    Try NSE official CSV first, fallback to Wikipedia, then to a small builtin list.
    Returns a list of tickers WITH .NS suffix (for yfinance).
    """
    # 1) official CSV from NSE archives
    csv_url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        resp = requests.get(csv_url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        # case-insensitive find Symbol column
        sym_col = next((c for c in df.columns if str(c).strip().lower() == "symbol"), None)
        if sym_col:
            syms = df[sym_col].dropna().astype(str).str.strip().tolist()
            syms = [s + ("" if s.endswith(".NS") else ".NS") for s in syms if s]
            if syms:
                return syms
    except Exception:
        pass

    # 2) fallback: Wikipedia NIFTY 500 table
    try:
        wiki = "https://en.wikipedia.org/wiki/NIFTY_500"
        tables = pd.read_html(wiki)
        if tables:
            df = max(tables, key=lambda t: t.shape[0])  # largest table
            cols = [str(c).strip().lower() for c in df.columns]
            for candidate in ("symbol", "ticker", "ticker symbol", "code", "scrip"):
                if candidate in cols:
                    sym_col = df.columns[cols.index(candidate)]
                    syms = df[sym_col].dropna().astype(str).str.strip().tolist()
                    syms = [s + ("" if s.endswith(".NS") else ".NS") for s in syms if s]
                    if syms:
                        return syms
    except Exception:
        pass

    # 3) final fallback small list
    return [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"
    ]


@st.cache_data(ttl=60 * 5)
def fetch_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Download price history and return DataFrame with a 'Date' column and standard OHLCV columns.
    Returns empty DataFrame on failure.
    """
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, threads=False)
        if df is None or df.empty:
            # fallback using Ticker.history
            t = yf.Ticker(symbol)
            df = t.history(period=period, interval=interval)
            if df is None or df.empty:
                return pd.DataFrame()

        # flatten MultiIndex columns if any
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join([str(x) for x in col if x is not None]).strip() for col in df.columns.values]

        # normalize column names
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

        # make sure required columns exist
        reqs = {"Open", "High", "Low", "Close"}
        if not reqs.issubset(set(df.columns)):
            return pd.DataFrame()

        df = df.reset_index()
        # ensure a 'Date' column exists (some dataframes use 'index' or other names after reset)
        if df.columns[0].lower() not in ("date", "datetime", "index"):
            df.rename(columns={df.columns[0]: "Date"}, inplace=True)
        else:
            df.rename(columns={df.columns[0]: "Date"}, inplace=True)

        # ensure numeric types
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        if "Volume" in df.columns:
            df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
        else:
            df["Volume"] = 0

        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60 * 60)
def fetch_company_info(symbol: str) -> dict:
    """Return selected fields from yfinance company info safely."""
    try:
        t = yf.Ticker(symbol)
        info = {}
        try:
            info = t.get_info() if hasattr(t, "get_info") else getattr(t, "info", {}) or {}
        except Exception:
            info = getattr(t, "info", {}) or {}
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

    # RSI (EWMA)
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
# UI & Layout
# -------------------------
st.set_page_config(page_title="Nifty 500 — Stock Dashboard", layout="wide")
st.title("📈 Nifty 500 Stock Dashboard")

# master dropdown
tickers = get_nifty500_tickers()
st.sidebar.markdown("### Select stock (NIFTY 500)")
# Display cleaner tickers (without .NS) but keep underlying values
options_display = [t[:-3] if t.endswith(".NS") else t for t in tickers]
selected_display = st.sidebar.selectbox("Ticker", options_display, index=0)
symbol = selected_display if selected_display.endswith(".NS") else selected_display + ".NS"
symbol_short = symbol.replace(".NS", "")

# Preload some data (default)
default_period = "6mo"
default_interval = "1d"
df = fetch_price_history(symbol, period=default_period, interval=default_interval)
if not df.empty:
    df = add_technical_indicators(df)

# Tabs
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
    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        period = st.selectbox("Period", ["1mo","3mo","6mo","1y","2y","5y","max"], index=2)
    with c2:
        interval = st.selectbox("Interval", ["1d","1wk","1mo"], index=0)
    with c3:
        show_sma = st.checkbox("Show SMA20/SMA50", True)
        show_ema = st.checkbox("Show EMA20/EMA50", False)
        show_rsi = st.checkbox("Show RSI(14)", False)
        show_macd = st.checkbox("Show MACD", False)

    df_chart = fetch_price_history(symbol, period=period, interval=interval)
    if df_chart.empty:
        st.warning("No price data available for this period/interval.")
    else:
        df_chart = add_technical_indicators(df_chart)
        # Plotly candlestick with volume and optional RSI/MACD
        rows = 2 + (1 if show_rsi else 0) + (1 if show_macd else 0)
        row_heights = [0.6, 0.2] + ([0.2] if show_rsi else []) + ([0.2] if show_macd else [])
        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=row_heights)

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df_chart['Date'], open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'],
            name="Price"
        ), row=1, col=1)

        # overlays
        if show_sma:
            if "SMA20" in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['SMA20'], name="SMA20", line=dict(width=1)), row=1, col=1)
            if "SMA50" in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['SMA50'], name="SMA50", line=dict(width=1)), row=1, col=1)
        if show_ema:
            if "EMA20" in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['EMA20'], name="EMA20", line=dict(dash="dot", width=1)), row=1, col=1)
            if "EMA50" in df_chart.columns: fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['EMA50'], name="EMA50", line=dict(dash="dot", width=1)), row=1, col=1)

        # Volume
        fig.add_trace(go.Bar(x=df_chart['Date'], y=df_chart.get('Volume', 0), name="Volume", marker=dict(opacity=0.6)), row=2, col=1)

        cur_row = 3
        if show_rsi:
            fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['RSI14'], name="RSI(14)"), row=cur_row, col=1)
            fig.add_hline(y=70, line_dash="dot", row=cur_row, col=1)
            fig.add_hline(y=30, line_dash="dot", row=cur_row, col=1)
            cur_row += 1
        if show_macd:
            fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['MACD'], name="MACD"), row=cur_row, col=1)
            fig.add_trace(go.Scatter(x=df_chart['Date'], y=df_chart['MACD_signal'], name="MACD Signal"), row=cur_row, col=1)
            fig.add_trace(go.Bar(x=df_chart['Date'], y=df_chart['MACD_hist'], name="MACD Hist"), row=cur_row, col=1)

        fig.update_layout(height=700, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

# Financials
with tab_fin:
    st.header(f"{symbol_short} — Financials (Yahoo)")
    t = yf.Ticker(symbol)
    try:
        fin = t.financials.transpose() if hasattr(t, "financials") else pd.DataFrame()
        bs = t.balance_sheet.transpose() if hasattr(t, "balance_sheet") else pd.DataFrame()
        cf = t.cashflow.transpose() if hasattr(t, "cashflow") else pd.DataFrame()
        if not fin.empty:
            st.subheader("Income Statement")
            st.dataframe(fin)
        else:
            st.info("Income statement not available.")
        if not bs.empty:
            st.subheader("Balance Sheet")
            st.dataframe(bs)
        else:
            st.info("Balance sheet not available.")
        if not cf.empty:
            st.subheader("Cash Flow")
            st.dataframe(cf)
        else:
            st.info("Cashflow not available.")
    except Exception:
        st.info("Financial statements not available for this ticker.")

# Technicals
with tab_tech:
    st.header(f"{symbol_short} — Technical Indicators")
    if df.empty:
        st.info("No price data to compute technicals.")
    else:
        last = df.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Close", f"{last['Close']:.2f}")
        c2.metric("SMA20", f"{last.get('SMA20', np.nan):.2f}")
        c3.metric("RSI(14)", f"{last.get('RSI14', np.nan):.2f}")
        c4.metric("MACD", f"{last.get('MACD', np.nan):.4f}")
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
            title = n.get("title") or "No title"
            link = n.get("link") or ""
            pub = n.get("time") or ""
            st.markdown(f"- [{title}]({link})  \n  _{pub}_")
