import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import requests
from datetime import datetime
from io import StringIO

# -------------------------------
# Helper Functions
# -------------------------------

def human_readable(num):
    if num is None: return "—"
    for unit in ["", "K", "M", "B", "T"]:
        if abs(num) < 1000.0:
            return f"{num:3.1f}{unit}"
        num /= 1000.0
    return f"{num:.1f}T"

def get_news(ticker):
    """Fetch latest news using Yahoo Finance API."""
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news[:5] if hasattr(stock, "news") else []
        return news_items
    except:
        return []

# -------------------------------
# Fetch Nifty 500 dynamically
# -------------------------------
@st.cache(allow_output_mutation=True)
def get_nifty500_tickers():
    url = "https://www1.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.nseindia.com/"
    }
    resp = requests.get(url, headers=headers, verify=False)  # SSL workaround
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    tickers = [f"{s}.NS" for s in df['Symbol']]
    names = df['Company Name'].tolist()
    return tickers, names

# -------------------------------
# Streamlit UI
# -------------------------------

st.set_page_config(page_title="Stock Monitoring Platform", layout="wide")
st.markdown("<h1 style='text-align:center'>📈 Stock Monitoring Platform</h1>", unsafe_allow_html=True)

# Get Nifty 500
tickers, names = get_nifty500_tickers()
ticker_map = dict(zip(names, tickers))
selected_name = st.selectbox("Select Stock (Nifty 500):", options=names)
ticker = ticker_map[selected_name]

stock = yf.Ticker(ticker)
info = stock.info

# Company Info
col1, col2 = st.columns([1,4])
with col1:
    if "logo_url" in info and info["logo_url"]:
        st.image(info["logo_url"], width=80)
with col2:
    st.subheader(info.get("shortName", ticker))

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Market Cap", human_readable(info.get("marketCap")))
col2.metric("P/E Ratio", round(info.get("trailingPE", 0), 2))
col3.metric("Dividend Yield", f"{round(info.get('dividendYield',0)*100,2)}%")
col4.metric("Beta", round(info.get("beta", 0), 2))

# Tabs
tabs = st.tabs(["Overview", "Financials", "Technicals", "News"])

# -------------------------------
# Overview Tab
# -------------------------------
with tabs[0]:
    st.subheader("Stock Price History")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]  # remove weekends

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"], name="Candlestick"))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Financials Tab
# -------------------------------
with tabs[1]:
    st.subheader("📊 Financial Performance")
    fin = stock.financials.T
    if not fin.empty:
        st.write("### Income Statement (Last Years)")
        st.dataframe(fin)

        fig = go.Figure()
        if "Total Revenue" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Total Revenue"], name="Revenue"))
        if "Net Income" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Net Income"], name="Net Income"))
        fig.update_layout(barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    bal = stock.balance_sheet.T
    if not bal.empty:
        with st.expander("📑 Balance Sheet"):
            st.dataframe(bal)

    cf = stock.cashflow.T
    if not cf.empty:
        with st.expander("💰 Cashflow Statement"):
            st.dataframe(cf)

# -------------------------------
# Technicals Tab
# -------------------------------
with tabs[2]:
    st.subheader("📈 Technical Analysis")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]

    hist["SMA20"] = hist["Close"].rolling(20).mean()
    hist["SMA50"] = hist["Close"].rolling(50).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", name="Close"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode="lines", name="SMA20"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode="lines", name="SMA50"))

    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# News Tab
# -------------------------------
with tabs[3]:
    st.subheader("📰 Latest News")
    news_items = get_news(ticker)
    if news_items:
        for item in news_items:
            col1, col2 = st.columns([1,5])
            with col1:
                if "thumbnail" in item and "resolutions" in item["thumbnail"]:
                    img = item["thumbnail"]["resolutions"][0]["url"]
                    st.image(img, width=80)
            with col2:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                st.caption(item.get("publisher", ""))
    else:
        st.info("No news available.")
