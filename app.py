import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objs as go
from bs4 import BeautifulSoup

# --------------------------
# Fetch Nifty 500 tickers
# --------------------------
@st.cache_data
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    df = pd.read_csv(url)
    tickers = df["Symbol"].tolist()
    return [ticker + ".NS" for ticker in tickers]

nifty_500_stocks = get_nifty500_tickers()

# --------------------------
# Fetch financials
# --------------------------
def get_financials(ticker):
    stock = yf.Ticker(ticker)
    try:
        financials = stock.financials
        return financials
    except:
        return pd.DataFrame()

# --------------------------
# Fetch technical indicators
# --------------------------
def get_technicals(df):
    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["RSI"] = compute_rsi(df["Close"])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --------------------------
# Fetch news from Yahoo Finance
# --------------------------
def get_news(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}?p={ticker}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    news_items = []
    for item in soup.find_all("h3", {"class": "Mb(5px)"}):
        title = item.get_text()
        link = item.find("a")["href"]
        if not link.startswith("http"):
            link = "https://finance.yahoo.com" + link
        news_items.append((title, link))

    return news_items[:5]

# --------------------------
# Streamlit UI
# --------------------------
st.set_page_config(page_title="NSE Stock Dashboard", layout="wide")

st.title("📈 Nifty 500 Stock Dashboard")

# Dropdown to select stock
selected_stock = st.selectbox("Select a stock:", nifty_500_stocks)

# Fetch stock data
stock_data = yf.download(selected_stock, period="6mo", interval="1d")
stock_data = get_technicals(stock_data)

# --------------------------
# Chart
# --------------------------
st.subheader("📊 Price Chart")
fig = go.Figure(data=[go.Candlestick(
    x=stock_data.index,
    open=stock_data["Open"],
    high=stock_data["High"],
    low=stock_data["Low"],
    close=stock_data["Close"],
    name="Candlesticks"
)])
fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data["SMA20"], mode="lines", name="SMA20"))
fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data["SMA50"], mode="lines", name="SMA50"))
st.plotly_chart(fig, use_container_width=True)

# --------------------------
# Financials
# --------------------------
st.subheader("📑 Financials")
financials = get_financials(selected_stock)
if not financials.empty:
    st.dataframe(financials)
else:
    st.write("No financial data available.")

# --------------------------
# Technical Indicators
# --------------------------
st.subheader("📐 Technicals")
st.line_chart(stock_data[["Close", "SMA20", "SMA50"]])
st.line_chart(stock_data[["RSI"]])

# --------------------------
# News
# --------------------------
st.subheader("📰 Latest News")
news = get_news(selected_stock.replace(".NS", ""))
for title, link in news:
    st.markdown(f"- [{title}]({link})")
