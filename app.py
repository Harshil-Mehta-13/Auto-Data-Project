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
    """Fetch Nifty 500 tickers dynamically from NSE India."""
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
    # Small company description
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
    st.subheader("Stock Price History (1 Year)")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]  # drop weekends

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"],
        name="Candlestick"
    ))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Financials Tab
# -------------------------------
with tabs[1]:
    st.subheader("📊 Financial Performance Charts")

    fin = stock.financials.T
    bal = stock.balance_sheet.T
    cf = stock.cashflow.T

    # Revenue & Net Income chart
    if not fin.empty:
        fig = go.Figure()
        if "Total Revenue" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Total Revenue"], name="Revenue"))
        if "Net Income" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Net Income"], name="Net Income"))
        fig.update_layout(
            title="Revenue & Net Income",
            xaxis_title="Year",
            yaxis_title="Amount",
            barmode="group"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Assets & Liabilities chart
    if not bal.empty:
        fig = go.Figure()
        if "Total Assets" in bal.columns:
            fig.add_trace(go.Bar(x=bal.index, y=bal["Total Assets"], name="Total Assets"))
        if "Total Liab" in bal.columns:
            fig.add_trace(go.Bar(x=bal.index, y=bal["Total Liab"], name="Total Liabilities"))
        fig.update_layout(
            title="Assets vs Liabilities",
            xaxis_title="Year",
            yaxis_title="Amount",
            barmode="group"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Cashflow chart
    if not cf.empty:
        fig = go.Figure()
        if "Total Cash From Operating Activities" in cf.columns:
            fig.add_trace(go.Bar(x=cf.index, y=cf["Total Cash From Operating Activities"], name="Operating Cashflow"))
        if "Capital Expenditures" in cf.columns:
            fig.add_trace(go.Bar(x=cf.index, y=cf["Capital Expenditures"], name="Capital Expenditure"))
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
    st.subheader("📈 Technical Analysis")
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
