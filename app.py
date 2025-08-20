import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import requests

# -------------------------------
# Helper functions
# -------------------------------

@st.cache_data
def get_nifty500_tickers():
    """Fetch Nifty 500 tickers dynamically from NSE"""
    url = "https://www1.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    df = pd.read_csv(url, headers=headers)
    tickers = [f"{s}.NS" for s in df['Symbol']]
    names = df['Company Name'].tolist() if 'Company Name' in df.columns else tickers
    return tickers, names

def get_news(ticker):
    """Fetch latest news using Yahoo Finance API (fallback simple HTML links)"""
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news[:5] if hasattr(stock, "news") else []
        return news_items
    except:
        return []

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

st.set_page_config(page_title="Nifty 500 Dashboard", layout="wide")

st.title("📊 Nifty 500 Stock Monitoring Platform")

# Get Nifty 500 tickers dynamically
tickers, names = get_nifty500_tickers()
ticker_dict = dict(zip(names, tickers))

selected_name = st.selectbox("Select Stock:", names)
selected_ticker = ticker_dict[selected_name]

# Fetch stock info and data
@st.cache_data
def load_data(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1y")
    info = stock.info
    return stock, data, info

stock, data, info = load_data(selected_ticker)

# -------------------------------
# Tabs for Navigation
# -------------------------------
tabs = st.tabs(["Overview", "Financials", "Charts", "News"])

# -------------------------------
# Overview Tab
# -------------------------------
with tabs[0]:
    st.subheader(f"📌 {info.get('longName', selected_ticker)} ({selected_ticker})")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"₹{info.get('currentPrice', 'N/A')}")
    col2.metric("Market Cap", human_readable(info.get('marketCap')))
    col3.metric("P/E Ratio", round(info.get('trailingPE', 0), 2))
    col4.metric("Beta", round(info.get('beta', 0), 2))

    st.write(info.get("longBusinessSummary", "No company summary available."))

# -------------------------------
# Financials Tab
# -------------------------------
with tabs[1]:
    st.subheader("📊 Financials")
    fin = stock.financials.T
    if not fin.empty:
        st.write("### Income Statement (Last Years)")
        st.dataframe(fin)

        # Revenue & Net Income chart
        fig = go.Figure()
        if "Total Revenue" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Total Revenue"], name="Revenue"))
        if "Net Income" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Net Income"], name="Net Income"))
        fig.update_layout(barmode="group", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Financial data not available.")

# -------------------------------
# Charts Tab
# -------------------------------
with tabs[2]:
    st.subheader("📈 Stock Price Charts")
    data = data[data.index.dayofweek < 5]  # Remove weekends

    # Candlestick chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'],
        name='Price'
    ))

    # Volume bars
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', opacity=0.3, marker_color='blue'))

    # SMA20 & SMA50
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()
    fig.add_trace(go.Scatter(x=data.index, y=data["SMA20"], mode="lines", name="SMA20", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=data.index, y=data["SMA50"], mode="lines", name="SMA50", line=dict(color="green")))

    fig.update_layout(title=f"{selected_ticker} Stock Price", template="plotly_white", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# News Tab
# -------------------------------
with tabs[3]:
    st.subheader("📰 Latest News")
    news_items = get_news(selected_ticker)
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
