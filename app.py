import pandas as pd
import requests

@st.cache_data
def get_nifty500_tickers():
    url = "https://www1.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.nseindia.com/"
    }
    resp = requests.get(url, headers=headers, verify=False)  # <-- ignore SSL issues
    resp.raise_for_status()
    
    from io import StringIO
    df = pd.read_csv(StringIO(resp.text))
    tickers = [f"{s}.NS" for s in df['Symbol']]
    names = df['Company Name'].tolist()
    return tickers, names
