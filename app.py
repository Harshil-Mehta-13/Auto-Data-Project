import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup

# ----------------------
# Load Nifty 500 Company List
# ----------------------
@st.cache_data
def load_nifty500():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    df = pd.read_csv(url)
    df = df[["Company Name", "Symbol"]]
    df.columns = ["Company", "Symbol"]
    return df

nifty500 = load_nifty500()

# ----------------------
# Persistent Dropdown (single master)
# ----------------------
if "selected_stock" not in st.session_state:
    st.session_state.selected_stock = "RELIANCE"

selected = st.selectbox(
    "Select Stock (Nifty 500)",
    options=nifty500["Symbol"].tolist(),
    index=nifty500[nifty500.Symbol == st.session_state.selected_stock].index[0] if st.session_state.selected_stock in nifty500.Symbol.values else 0,
)
st.session_state.selected_stock = selected

symbol = selected + ".NS"
company_name = nifty500.loc[nifty500.Symbol == selected, "Company"].values[0]

st.title(f"📈 {company_name} ({selected}) Dashboard")

# ----------------------
# Fetch Financial Data (Yahoo Finance)
# ----------------------
@st.cache_data
def get_stock_data(symbol, period="6mo"):
    return yf.download(symbol, period=period)

@st.cache_data
def get_info(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info

stock_data = get_stock_data(symbol)
info = get_info(symbol)

# ----------------------
# Price Chart
# ----------------------
fig = go.Figure(data=[go.Candlestick(
    x=stock_data.index,
    open=stock_data['Open'],
    high=stock_data['High'],
    low=stock_data['Low'],
    close=stock_data['Close']
)])
fig.update_layout(title=f"{selected} - Price Chart", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# ----------------------
# Financial Summary (Yahoo + Screener)
# ----------------------
st.subheader("Financial Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Current Price", f"₹{info.get('currentPrice', 'NA')}")
    st.metric("Market Cap", f"₹{round(info.get('marketCap', 0)/1e7,2)} Cr")

with col2:
    st.metric("PE Ratio", info.get("trailingPE", "NA"))
    st.metric("PB Ratio", info.get("priceToBook", "NA"))

with col3:
    st.metric("52W High", info.get("fiftyTwoWeekHigh", "NA"))
    st.metric("52W Low", info.get("fiftyTwoWeekLow", "NA"))

# ----------------------
# Screener.in Data (Extra Financials)
# ----------------------
@st.cache_data
def get_screener_data(symbol):
    try:
        url = f"https://www.screener.in/company/{symbol}/"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("section", {"id": "top-ratios"})
        data = {}
        if table:
            for row in table.find_all("li"):
                key = row.find("span", {"class": "name"}).text.strip()
                val = row.find("span", {"class": "value"}).text.strip()
                data[key] = val
        return data
    except:
        return {}

screener_data = get_screener_data(selected)

if screener_data:
    st.subheader("Key Ratios (Screener.in)")
    st.dataframe(pd.DataFrame(list(screener_data.items()), columns=["Metric", "Value"]))

# ----------------------
# Tabs for More Data
# ----------------------

info_tab, hist_tab, fin_tab = st.tabs(["📊 Company Info", "📉 Historical Data", "💰 Financials"])

with info_tab:
    st.write(info)

with hist_tab:
    st.dataframe(stock_data.tail(30))

with fin_tab:
    st.json(info.get("financialsTemplate", {}))
