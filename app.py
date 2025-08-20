import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go

# Load full Nifty 500 tickers from CSV (replace with your file)
nifty500 = pd.read_csv("nifty500.csv")  # should have a column 'Symbol'
tickers = [f"{s}.NS" for s in nifty500['Symbol']]

# Sidebar for ticker selection
st.sidebar.header("📈 Nifty 500 Dashboard")
selected_ticker = st.sidebar.selectbox("Select Company", tickers)

# Download data
@st.cache_data
def load_data(ticker):
    data = yf.download(ticker, period="1y", interval="1d")
    info = yf.Ticker(ticker).info
    return data, info

data, info = load_data(selected_ticker)

# Tabs like TradingView
page = st.sidebar.radio("Navigate", ["Overview", "Financials", "Charts", "News"])

# ----------------- Overview -----------------
if page == "Overview":
    st.title(f"{info.get('longName', selected_ticker)} ({selected_ticker})")

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"₹{info.get('currentPrice', 'N/A')}")
    col2.metric("Market Cap", f"₹{info.get('marketCap', 'N/A'):,}")
    col3.metric("P/E Ratio", info.get('trailingPE', 'N/A'))

    st.subheader("About")
    st.write(info.get("longBusinessSummary", "No company summary available."))

# ----------------- Financials -----------------
elif page == "Financials":
    st.title("📊 Financials")

    # Income statement (last few years)
    ticker_obj = yf.Ticker(selected_ticker)
    fin = ticker_obj.financials

    if fin is not None and not fin.empty:
        st.write("### Income Statement")
        st.dataframe(fin)

        # Plot revenue & net income trends
        if "Total Revenue" in fin.index and "Net Income" in fin.index:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=fin.columns, y=fin.loc["Total Revenue"], name="Revenue"))
            fig.add_trace(go.Bar(x=fin.columns, y=fin.loc["Net Income"], name="Net Income"))
            fig.update_layout(barmode="group", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Financial data not available for this company.")

# ----------------- Charts -----------------
elif page == "Charts":
    st.title("📉 Charts")

    fig = go.Figure()

    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price'
    ))

    # Add volume bar chart
    fig.add_trace(go.Bar(x=data.index, y=data['Volume'], name='Volume', opacity=0.3, marker_color='blue'))

    fig.update_layout(
        title=f"{selected_ticker} Stock Price",
        yaxis_title="Price (₹)",
        xaxis_title="Date",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

# ----------------- News -----------------
elif page == "News":
    st.title("📰 News")
    st.info("News integration (e.g., Google News API) can be added here.")
