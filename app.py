import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Hello Streamlit", layout="wide")
st.title("🚀 Hello, Streamlit!")

st.write("Current time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

n = st.slider("Number of points", 20, 300, 100)
rng = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="min")
data = pd.DataFrame({"value": np.random.randn(n).cumsum()}, index=rng)

st.line_chart(data)
