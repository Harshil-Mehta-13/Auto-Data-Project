import streamlit as st
import pandas as pd
import yfinance as yf

st.title("📈 Stock Portfolio Tracker")

# Upload Excel file
uploaded_file = st.file_uploader("Upload your portfolio Excel file", type=["xlsx"])

if uploaded_file:
    # Read Excel
    df = pd.read_excel(uploaded_file)

    # Ensure correct column names
    if all(col in df.columns for col in ["Ticker", "Avg_Buy_Price", "Quantity"]):
        st.write("✅ Portfolio uploaded successfully!")
        
        results = []
        
        for index, row in df.iterrows():
            ticker = row["Ticker"]
            avg_price = row["Avg_Buy_Price"]
            qty = row["Quantity"]
            
            # Get real-time stock data
            stock = yf.Ticker(ticker)
            current_price = stock.history(period="1d")["Close"].iloc[-1]
            
            investment = avg_price * qty
            current_value = current_price * qty
            profit_loss = current_value - investment
            return_pct = (profit_loss / investment) * 100 if investment > 0 else 0
            
            results.append({
                "Ticker": ticker,
                "Avg Price": avg_price,
                "Quantity": qty,
                "Current Price": round(current_price, 2),
                "Investment": round(investment, 2),
                "Current Value": round(current_value, 2),
                "P/L": round(profit_loss, 2),
                "Return %": round(return_pct, 2)
            })
        
        results_df = pd.DataFrame(results)
        
        st.dataframe(results_df)

        # Portfolio Summary
        total_investment = results_df["Investment"].sum()
        total_value = results_df["Current Value"].sum()
        total_profit = results_df["P/L"].sum()
        total_return_pct = (total_profit / total_investment) * 100 if total_investment > 0 else 0
        
        st.subheader("📊 Portfolio Summary")
        st.metric("Total Investment", f"₹{total_investment:,.2f}")
        st.metric("Current Value", f"₹{total_value:,.2f}")
        st.metric("Total P/L", f"₹{total_profit:,.2f}")
        st.metric("Return %", f"{total_return_pct:.2f}%")
    else:
        st.error("❌ Excel must have columns: Ticker, Avg_Buy_Price, Quantity")
