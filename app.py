import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import datetime
import requests

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="📈 Stock Monitoring Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ CUSTOM CSS ------------------
st.markdown(
    """
    <style>
    /* Title Styling */
    .title {
        font-size: 38px;
        font-weight: 700;
        text-align: center;
        color: #111;
        padding-bottom: 5px;
    }
    .subtitle {
        font-size: 18px;
        text-align: center;
        color: #555;
        margin-bottom: 25px;
    }
    /* Dropdown compact */
    .stSelectbox > div > div {
        max-width: 300px;
        margin: auto;
    }
    /* News cards */
    .news-card {
        display: flex;
        align-items: center;
        background: #f9f9f9;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 10px;
        transition: 0.3s;
    }
    .news-card:hover {
        background: #ececec;
        transform: scale(1.01);
    }
    .news-thumb {
        width: 60px;
        height: 60px;
        border-radius: 8px;
        margin-right: 15px;
        object-fit: cover;
    }
    .news-title {
        font-size: 16px;
        font-weight: 600;
        color: #333;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------ TITLE ------------------
st.markdown('<div class="title">📊 Stock Monitoring Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Track performance, analyze trends & stay updated with news in one place</div>', unsafe_allow_html=True)

# ------------------ SIDEBAR ------------------
st.sidebar.header("⚙️ Settings")
ticker = st.sidebar.selectbox("Select Stock Ticker", ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"], index=0)
segment = st.sidebar.radio("🔎 Navigate", ["Overview", "Financials", "Technicals", "News"])

start_date = st.sidebar.date_input("Start Date", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())

# ------------------ DATA FETCH ------------------
stock = yf.Ticker(ticker)
df = yf.download(ticker, start=start_date, end=end_date, progress=False)

# Remove weekends (only weekdays)
df = df[df.index.dayofweek < 5]

# ------------------ SEGMENTS ------------------
if segment == "Overview":
    st.subheader(f"📌 {ticker} - Overview")
    st.write(stock.info.get("longBusinessSummary", "No description available."))

    # Candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    )])
    fig.update_layout(title=f"{ticker} Price Movement", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

elif segment == "Financials":
    st.subheader(f"💰 {ticker} - Financials")

    fin = stock.financials
    bs = stock.balance_sheet
    cf = stock.cashflow

    # Convert to DataFrame for plotting
    if not fin.empty:
        fin_chart = fin.T
        st.write("### Income Statement Trends")
        st.line_chart(fin_chart)

    if not bs.empty:
        st.write("### Balance Sheet Breakdown")
        bs_chart = bs.T
        st.bar_chart(bs_chart)

    if not cf.empty:
        st.write("### Cashflow Overview")
        cf_chart = cf.T
        st.area_chart(cf_chart)

elif segment == "Technicals":
    st.subheader(f"📉 {ticker} - Technical Analysis")

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Close"))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], mode="lines", name="SMA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], mode="lines", name="SMA50"))
    fig.update_layout(title=f"{ticker} Technical Indicators")
    st.plotly_chart(fig, use_container_width=True)

elif segment == "News":
    st.subheader(f"📰 Latest News for {ticker}")
    query = ticker
    url = f"https://newsapi.org/v2/everything?q={query}&apiKey=demo"  # Replace demo with your NewsAPI key
    try:
        r = requests.get(url)
        articles = r.json().get("articles", [])[:5]

        if articles:
            for a in articles:
                thumb = a.get("urlToImage", "https://via.placeholder.com/60")
                title = a.get("title", "")
                link = a.get("url", "#")

                st.markdown(
                    f"""
                    <a href="{link}" target="_blank" class="news-card">
                        <img src="{thumb}" class="news-thumb">
                        <div class="news-title">{title}</div>
                    </a>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No news found at the moment.")
    except Exception:
        st.warning("⚠️ Unable to fetch news right now. Please check your API key.")
