import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go

# -------------------------------
# Helper functions
# -------------------------------

def get_news(ticker):
    """Fetch latest news using Yahoo Finance API (fallback to simple HTML links)."""
    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news[:6] if hasattr(stock, "news") else []
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
st.set_page_config(page_title="Stock Monitoring Platform", layout="wide")

# Apple-like clean style
st.markdown(
    """
    <style>
    .title {
        text-align: center;
        font-size: 40px;
        font-weight: 700;
        margin-top: 10px;
        margin-bottom: 5px;
    }
    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #666;
        margin-bottom: 20px;
    }
    .stSelectbox, .stRadio {
        margin: auto;
        max-width: 400px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<div class='title'>📊 Stock Monitoring Platform</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Track Financials • Technicals • News</div>", unsafe_allow_html=True)

# Example: Nifty 500 tickers (partial list for demo)
nifty500 = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "HINDUNILVR.NS"]

col1, col2 = st.columns([2,3])
with col1:
    ticker = st.selectbox("Select Stock:", nifty500)
with col2:
    section = st.radio("Select Section:", ["Overview", "Financials", "Technicals", "News"], horizontal=True)

stock = yf.Ticker(ticker)
info = stock.info

# -------------------------------
# Company Header
# -------------------------------
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

# -------------------------------
# Overview Section
# -------------------------------
if section == "Overview":
    st.subheader("📈 Stock Price History")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]  # drop weekends

    fig = go.Figure(data=[go.Candlestick(
        x=hist.index,
        open=hist["Open"], high=hist["High"],
        low=hist["Low"], close=hist["Close"],
        name="Price"
    )])
    fig.update_layout(template="plotly_white", height=500, margin=dict(l=30,r=30,t=30,b=30))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Financials Section
# -------------------------------
elif section == "Financials":
    st.subheader("💰 Financial Performance")

    fin = stock.financials.T
    if not fin.empty:
        st.write("### Income Statement (Visualized)")
        fig = go.Figure()
        if "Total Revenue" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Total Revenue"], name="Revenue", marker_color="steelblue"))
        if "Net Income" in fin.columns:
            fig.add_trace(go.Bar(x=fin.index, y=fin["Net Income"], name="Net Income", marker_color="seagreen"))
        fig.update_layout(barmode="group", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    bal = stock.balance_sheet.T
    if not bal.empty:
        st.write("### Balance Sheet Highlights")
        fig_bal = go.Figure()
        if "Total Assets" in bal.columns:
            fig_bal.add_trace(go.Scatter(x=bal.index, y=bal["Total Assets"], name="Total Assets", line=dict(color="blue")))
        if "Total Liab" in bal.columns:
            fig_bal.add_trace(go.Scatter(x=bal.index, y=bal["Total Liab"], name="Total Liabilities", line=dict(color="red")))
        fig_bal.update_layout(template="plotly_white")
        st.plotly_chart(fig_bal, use_container_width=True)

    cf = stock.cashflow.T
    if not cf.empty:
        st.write("### Cashflow Trends")
        fig_cf = go.Figure()
        if "Total Cash From Operating Activities" in cf.columns:
            fig_cf.add_trace(go.Bar(x=cf.index, y=cf["Total Cash From Operating Activities"], name="Operating CF"))
        if "Capital Expenditures" in cf.columns:
            fig_cf.add_trace(go.Bar(x=cf.index, y=cf["Capital Expenditures"], name="CapEx"))
        fig_cf.update_layout(barmode="group", template="plotly_white")
        st.plotly_chart(fig_cf, use_container_width=True)

# -------------------------------
# Technicals Section
# -------------------------------
elif section == "Technicals":
    st.subheader("📊 Technical Indicators")
    hist = stock.history(period="1y")
    hist = hist[hist.index.dayofweek < 5]

    # SMA/EMA
    hist["SMA20"] = hist["Close"].rolling(20).mean()
    hist["EMA50"] = hist["Close"].ewm(span=50).mean()

    fig_ta = go.Figure()
    fig_ta.add_trace(go.Scatter(x=hist.index, y=hist["Close"], name="Close", line=dict(color="black")))
    fig_ta.add_trace(go.Scatter(x=hist.index, y=hist["SMA20"], name="SMA20", line=dict(color="blue", dash="dot")))
    fig_ta.add_trace(go.Scatter(x=hist.index, y=hist["EMA50"], name="EMA50", line=dict(color="red", dash="dash")))
    fig_ta.update_layout(template="plotly_white")
    st.plotly_chart(fig_ta, use_container_width=True)

    # RSI
    delta = hist["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    hist["RSI"] = 100 - (100 / (1 + rs))

    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=hist.index, y=hist["RSI"], name="RSI", line=dict(color="purple")))
    fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
    fig_rsi.update_layout(template="plotly_white", height=300)
    st.plotly_chart(fig_rsi, use_container_width=True)

# -------------------------------
# News Section
# -------------------------------
elif section == "News":
    st.subheader("📰 Latest News")
    news_items = get_news(ticker)
    if news_items:
        for item in news_items:
            col1, col2 = st.columns([1,5])
            with col1:
                if "thumbnail" in item and "resolutions" in item["thumbnail"]:
                    img = item["thumbnail"]["resolutions"][0]["url"]
                    st.image(img, width=100)
            with col2:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                st.caption(item.get("publisher", ""))
    else:
        st.info("No news available.")
