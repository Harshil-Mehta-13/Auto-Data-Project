import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime

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
    """Fetch latest news using Yahoo Finance API"""
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news[:5] if hasattr(stock, "news") else []
        return news_items
    except:
        return []

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="Stock Monitoring Platform", layout="wide")
st.markdown("<h1 style='text-align: center;'>📈 Stock Monitoring Platform</h1>", unsafe_allow_html=True)

# Example: Nifty 500 tickers (for demo, replace with all tickers in production)
nifty500 = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "HINDUNILVR.NS"]

ticker = st.selectbox("Select Stock:", nifty500)

stock = yf.Ticker(ticker)
info = stock.info

# -------------------------------
# Company Info
# -------------------------------
col1, col2 = st.columns([1,4])
with col1:
    if "logo_url" in info and info["logo_url"]:
        st.image(info["logo_url"], width=80)
with col2:
    st.subheader(info.get("shortName", ticker))
    st.markdown(info.get("longBusinessSummary", "No summary available.")[:250] + "...")

# -------------------------------
# KPIs
# -------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Market Cap", human_readable(info.get("marketCap")))
col2.metric("P/E Ratio", round(info.get("trailingPE", 0), 2))
col3.metric("Dividend Yield", f"{round(info.get('dividendYield',0)*100,2)}%")
col4.metric("Beta", round(info.get("beta", 0), 2))

# -------------------------------
# Tabs
# -------------------------------
tab = st.radio("Sections:", ["Overview", "Financials", "Technicals", "News"], horizontal=True)

# -------------------------------
# Overview Tab
# -------------------------------
if tab == "Overview":
    st.subheader("📊 Stock Price History")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]  # remove weekends

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index,
                                 open=hist["Open"], high=hist["High"],
                                 low=hist["Low"], close=hist["Close"],
                                 name="Candlestick"))

    sma_options = st.multiselect("Indicators:", ["SMA20","SMA50"], default=[])
    if "SMA20" in sma_options:
        hist["SMA20"] = hist["Close"].rolling(20).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode="lines", name="SMA20"))
    if "SMA50" in sma_options:
        hist["SMA50"] = hist["Close"].rolling(50).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode="lines", name="SMA50"))

    fig.update_layout(xaxis_rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Financials Tab
# -------------------------------
elif tab == "Financials":
    st.subheader("📊 Financials Overview")

    fin = stock.financials.T
    if not fin.empty:
        st.markdown("### Income Statement Waterfall")
        # Use waterfall chart for Revenue → Expenses → Net Income
        rev = fin.get("Total Revenue")
        net = fin.get("Net Income")
        if rev is not None and net is not None:
            fig = go.Figure(go.Waterfall(
                x=rev.index,
                measure=["relative"]*len(rev),
                y=rev.values,
                name="Revenue"
            ))
            st.plotly_chart(fig, use_container_width=True)

        metrics_options = st.multiselect("Select metrics to visualize:", fin.columns.tolist(), default=["Total Revenue","Net Income"])
        fig2 = go.Figure()
        for metric in metrics_options:
            if metric in fin.columns:
                fig2.add_trace(go.Bar(x=fin.index, y=fin[metric], name=metric))
        st.plotly_chart(fig2, use_container_width=True)

    bal = stock.balance_sheet.T
    if not bal.empty:
        st.markdown("### Balance Sheet")
        metrics_bal = st.multiselect("Balance Sheet Metrics:", bal.columns.tolist(), default=["Total Assets","Total Liab"])
        fig3 = go.Figure()
        for metric in metrics_bal:
            if metric in bal.columns:
                fig3.add_trace(go.Bar(x=bal.index, y=bal[metric], name=metric))
        st.plotly_chart(fig3, use_container_width=True)

    cf = stock.cashflow.T
    if not cf.empty:
        st.markdown("### Cashflow")
        metrics_cf = st.multiselect("Cashflow Metrics:", cf.columns.tolist(), default=["Total Cash From Operating Activities"])
        fig4 = go.Figure()
        for metric in metrics_cf:
            if metric in cf.columns:
                fig4.add_trace(go.Bar(x=cf.index, y=cf[metric], name=metric))
        st.plotly_chart(fig4, use_container_width=True)

# -------------------------------
# Technicals Tab
# -------------------------------
elif tab == "Technicals":
    st.subheader("📈 Technical Analysis")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]

    timeframe = st.selectbox("Timeframe:", ["1y","6mo","3mo","1mo"])
    hist = stock.history(period=timeframe)
    hist = hist[hist.index.dayofweek < 5]

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index,
                                 open=hist["Open"], high=hist["High"],
                                 low=hist["Low"], close=hist["Close"],
                                 name="Candlestick"))

    indicators = st.multiselect("Indicators:", ["SMA20","SMA50","SMA100"])
    if "SMA20" in indicators: hist["SMA20"] = hist["Close"].rolling(20).mean(); fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], mode="lines", name="SMA20"))
    if "SMA50" in indicators: hist["SMA50"] = hist["Close"].rolling(50).mean(); fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA50"], mode="lines", name="SMA50"))
    if "SMA100" in indicators: hist["SMA100"] = hist["Close"].rolling(100).mean(); fig.add_trace(go.Scatter(x=hist.index, y=hist["SMA100"], mode="lines", name="SMA100"))

    fig.update_layout(xaxis_rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# News Tab
# -------------------------------
elif tab == "News":
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
                st.markdown(f"**[{item.get('title','No title')}]({item.get('link','#')})**")
                st.caption(item.get("publisher", ""))
    else:
        st.info("No news available.")
