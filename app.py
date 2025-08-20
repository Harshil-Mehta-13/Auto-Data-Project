import streamlit as st
import pandas as pd

# -------------------------------
# Function to get Nifty 500 stocks
# -------------------------------
@st.cache_data
def get_nifty500_stocks():
    url = "https://en.wikipedia.org/wiki/NIFTY_500"
    try:
        tables = pd.read_html(url)
        if not tables:
            st.error("No tables found on Wikipedia page.")
            return pd.DataFrame()

        # Pick the largest table (usually the stock list)
        df = max(tables, key=lambda t: t.shape[0])

        # Clean column names
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        return df

    except Exception as e:
        st.error(f"Error fetching Nifty 500 stocks: {e}")
        return pd.DataFrame()

# -------------------------------
# Streamlit App Layout
# -------------------------------
st.set_page_config(page_title="Nifty 500 Screener", layout="wide")

st.title("📊 Nifty 500 Stock Screener")

nifty_500_stocks = get_nifty500_stocks()

if not nifty_500_stocks.empty:
    st.success(f"Fetched {len(nifty_500_stocks)} stocks successfully ✅")

    st.dataframe(nifty_500_stocks.head(20))  # Show top 20 as preview

    # Optional: Add filters
    all_columns = nifty_500_stocks.columns.tolist()
    st.sidebar.subheader("🔍 Filters")

    if all_columns:
        col_to_filter = st.sidebar.selectbox("Select column to filter", all_columns)
        filter_text = st.sidebar.text_input("Enter filter text")

        if filter_text:
            filtered_df = nifty_500_stocks[
                nifty_500_stocks[col_to_filter].astype(str).str.contains(filter_text, case=False, na=False)
            ]
            st.dataframe(filtered_df)
        else:
            st.dataframe(nifty_500_stocks)

else:
    st.error("⚠️ Could not fetch Nifty 500 stocks. Please check Wikipedia table structure.")
