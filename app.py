import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# ===============================
# Function to fetch NIFTY 500 tickers from NSE CSV
# ===============================
@st.cache_data
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        df = pd.read_csv(url)
        df = df.rename(columns=lambda x: x.strip())
        tickers = df["Symbol"].dropna().astype(str).tolist()
        return [t + ".NS" for t in tickers]  # append .NS for Yahoo Finance
    except Exception as e:
        st.error(f"Failed to load NIFTY 500 list: {e}")
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

# ===============================
# Function to fetch live stock data
# ===============================
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo", interval="1d")
    return hist

# ===============================
# Function to calculate portfolio performance
# ===============================
def calculate_portfolio(df):
    results = []
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        qty = row["Quantity"]
        avg_price = row["Avg Price"]

        try:
            stock = yf.Ticker(ticker)
            live_price = stock.history(period="1d")["Close"].iloc[-1]
            invested = avg_price * qty
            current_value = live_price * qty
            pnl = current_value - invested
            results.append([ticker, avg_price, qty, live_price, invested, current_value, pnl])
        except Exception:
            continue

    return pd.DataFrame(results, columns=["Ticker", "Avg Price", "Quantity", "Live Price", "Invested", "Current Value", "P&L"])

# ===============================
# Streamlit UI
# ===============================
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")
st.title("📈 Stock Portfolio Tracker")

# Fetch NIFTY 500 tickers
nifty_500_stocks = get_nifty500_tickers()
st.sidebar.success(f"✅ Loaded {len(nifty_500_stocks)} NIFTY 500 tickers")

# Upload portfolio Excel
uploaded_file = st.file_uploader("Upload Portfolio Excel (Ticker, Avg Price, Quantity)", type=["xlsx"])
if uploaded_file:
    portfolio_df = pd.read_excel(uploaded_file)

    # Calculate performance
    result_df = calculate_portfolio(portfolio_df)

    st.subheader("📊 Portfolio Summary")
    st.dataframe(result_df, use_container_width=True)

    total_invested = result_df["Invested"].sum()
    total_value = result_df["Current Value"].sum()
    total_pnl = result_df["P&L"].sum()

    st.metric("💰 Total Invested", f"₹{total_invested:,.2f}")
    st.metric("📈 Current Value", f"₹{total_value:,.2f}")
    st.metric("🔄 P&L", f"₹{total_pnl:,.2f}")

    # Stock chart
    st.subheader("📉 Stock Chart")
    selected_stock = st.selectbox("Choose a stock", result_df["Ticker"].unique())

    if selected_stock:
        hist_data = get_stock_data(selected_stock)
        fig = go.Figure(data=[go.Candlestick(
            x=hist_data.index,
            open=hist_data['Open'],
            high=hist_data['High'],
            low=hist_data['Low'],
            close=hist_data['Close']
        )])
        fig.update_layout(title=f"{selected_stock} - Price Chart", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📤 Please upload your portfolio Excel file to begin.")
