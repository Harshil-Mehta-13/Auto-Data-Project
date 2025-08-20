import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# -------------------------------------------
# Fetch Nifty 500 stock tickers
# -------------------------------------------
@st.cache_data
def get_nifty500_stocks():
    url = "https://en.wikipedia.org/wiki/NIFTY_500"
    tables = pd.read_html(url)
    df = tables[1]  # The table containing company list
    return df['Symbol'].tolist()

nifty_500_stocks = get_nifty500_stocks()

# -------------------------------------------
# App Layout
# -------------------------------------------
st.set_page_config(page_title="Stock Analysis App", layout="wide")
st.title("📈 Nifty 500 Stock Analysis Dashboard")

# Sidebar for stock selection
stock = st.sidebar.selectbox("Select a Stock", nifty_500_stocks)

# Download stock data
ticker = yf.Ticker(stock + ".NS") if not stock.endswith(".NS") else yf.Ticker(stock)

# -------------------------------------------
# Stock Price Chart
# -------------------------------------------
st.subheader(f"Stock Price - {stock}")
period = st.selectbox("Select Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
interval = st.selectbox("Select Interval", ["1d", "1wk", "1mo"], index=0)

data = ticker.history(period=period, interval=interval)
st.line_chart(data['Close'])

# -------------------------------------------
# Company Financials
# -------------------------------------------
st.subheader("📊 Company Financials")
try:
    fin = ticker.financials
    bs = ticker.balance_sheet
    cf = ticker.cashflow
    st.write("### Income Statement")
    st.dataframe(fin)
    st.write("### Balance Sheet")
    st.dataframe(bs)
    st.write("### Cash Flow")
    st.dataframe(cf)
except Exception as e:
    st.warning("Financial data not available.")

# -------------------------------------------
# Technical Indicators
# -------------------------------------------
st.subheader("📈 Technical Analysis")

def calculate_technical_indicators(data):
    df = data.copy()
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['RSI'] = 100 - (100 / (1 + df['Close'].pct_change().rolling(14).apply(
        lambda x: (x[x > 0].mean() / (-x[x < 0].mean())) if (-x[x < 0].mean()) != 0 else 0)))
    return df

data_ta = calculate_technical_indicators(data)
st.line_chart(data_ta[['Close', 'SMA20', 'SMA50']])
st.write("Latest RSI:", round(data_ta['RSI'].iloc[-1], 2))

# -------------------------------------------
# News Section (Free Source)
# -------------------------------------------
st.subheader("📰 Latest News")

def get_news(query):
    url = f"https://news.google.com/rss/search?q={query}+stock+India"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")[:5]
    news_list = []
    for item in items:
        news_list.append({
            "title": item.title.text,
            "link": item.link.text,
            "pubDate": item.pubDate.text
        })
    return news_list

news = get_news(stock)
for n in news:
    st.markdown(f"- [{n['title']}]({n['link']}) ({n['pubDate']})")
