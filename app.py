import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime

# -------------------------------
# Helper functions
# -------------------------------
@st.cache_data
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    df = pd.read_csv(url)
    tickers = [symbol + ".NS" for symbol in df['Symbol']]
    names = df['Company Name'].tolist()
    return tickers, names

def human_readable(num):
    if num is None: return "—"
    for unit in ["", "K", "M", "B", "T"]:
        if abs(num) < 1000.0:
            return f"{num:3.1f}{unit}"
        num /= 1000.0
    return f"{num:.1f}T"

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Stock Monitoring Platform", layout="wide")
st.markdown("<h1 style='text-align:center;'>📊 Stock Monitoring Platform</h1>", unsafe_allow_html=True)

# Fetch tickers
tickers, names = get_nifty500_tickers()
ticker_idx = st.selectbox(
    "Select Stock (Nifty 500):",
    options=range(len(tickers)),
    format_func=lambda x: f"{tickers[x]} - {names[x]}"
)
ticker = tickers[ticker_idx]
stock = yf.Ticker(ticker)
info = stock.info

# Company header
col1, col2 = st.columns([1,4])
with col1:
    if "logo_url" in info and info["logo_url"]:
        st.image(info["logo_url"], width=80)
with col2:
    st.subheader(info.get("shortName", ticker))
    st.markdown(info.get("longBusinessSummary", "Description not available.")[:250] + "...")

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Market Cap", human_readable(info.get("marketCap")))
col2.metric("P/E Ratio", round(info.get("trailingPE", 0), 2))
col3.metric("Dividend Yield", f"{round(info.get('dividendYield',0)*100,2)}%")
col4.metric("Beta", round(info.get("beta", 0), 2))

# Tabs
tabs = st.tabs(["Overview", "Financials", "Technicals"])

# -------------------------------
# Overview Tab
# -------------------------------
with tabs[0]:
    st.subheader("📈 Stock Price History (1 Year)")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]  # drop weekends

    chart_type = st.selectbox("Chart Type:", ["Candlestick", "Line"])
    show_sma = st.checkbox("Show SMA20/SMA50")

    if show_sma:
        hist["SMA20"] = hist["Close"].rolling(20).mean()
        hist["SMA50"] = hist["Close"].rolling(50).mean()

    fig = go.Figure()
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"],
            name="Candlestick"
        ))
    else:
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Close"))

    if show_sma:
        fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode="lines", name="SMA20"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode="lines", name="SMA50"))

    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Financials Tab
# -------------------------------
with tabs[1]:
    st.subheader("📊 Financial Performance Charts")

    fin = stock.financials.T
    bal = stock.balance_sheet.T
    cf = stock.cashflow.T

    # Income Statement charts
    if not fin.empty:
        metrics = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income"]
        fig = go.Figure()
        for metric in metrics:
            if metric in fin.columns:
                fig.add_trace(go.Bar(x=fin.index, y=fin[metric], name=metric))
        fig.update_layout(
            title="Income Statement Overview",
            xaxis_title="Year",
            yaxis_title="Amount",
            barmode="group"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Balance Sheet charts
    if not bal.empty:
        metrics = ["Total Assets", "Total Liab", "Total Stockholder Equity"]
        fig = go.Figure()
        for metric in metrics:
            if metric in bal.columns:
                fig.add_trace(go.Bar(x=bal.index, y=bal[metric], name=metric))
        fig.update_layout(
            title="Balance Sheet Overview",
            xaxis_title="Year",
            yaxis_title="Amount",
            barmode="group"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Cashflow charts
    if not cf.empty:
        metrics = ["Total Cash From Operating Activities", "Capital Expenditures", "Total Cash From Financing Activities"]
        fig = go.Figure()
        for metric in metrics:
            if metric in cf.columns:
                fig.add_trace(go.Bar(x=cf.index, y=cf[metric], name=metric))
        fig.update_layout(
            title="Cashflow Overview",
            xaxis_title="Year",
            yaxis_title="Amount",
            barmode="group"
        )
        st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Technicals Tab
# -------------------------------
with tabs[2]:
    st.subheader("📊 Technical Analysis")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]

    # SMA
    hist["SMA20"] = hist["Close"].rolling(20).mean()
    hist["SMA50"] = hist["Close"].rolling(50).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Close"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode="lines", name="SMA20"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode="lines", name="SMA50"))
    st.plotly_chart(fig, use_container_width=True)
