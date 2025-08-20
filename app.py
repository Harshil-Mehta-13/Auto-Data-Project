# app.py
import io
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import requests
from bs4 import BeautifulSoup

# -------------------------
# Helpers / Data fetchers
# -------------------------
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

@st.cache_data(ttl=60 * 60 * 24)  # refresh daily
def get_nifty500_tickers():
    """
    Try NSE official CSV first, fallback to Wikipedia parsing, then to a small builtin list.
    Returns list of tickers *with* .NS suffix (for yfinance).
    """
    # 1) official CSV
    csv_url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        resp = requests.get(csv_url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        # common column name 'Symbol'
        if any(col.lower() == "symbol" for col in df.columns):
            # Find 'Symbol' case-insensitively
            sym_col = next(c for c in df.columns if c.lower() == "symbol")
            syms = df[sym_col].dropna().astype(str).str.strip().tolist()
            syms = [s + ("" if s.endswith(".NS") else ".NS") for s in syms if s]
            if syms:
                return syms
    except Exception:
        # ignore and fallback
        pass

    # 2) Try Wikipedia table (less official but often works)
    try:
        wiki = "https://en.wikipedia.org/wiki/NIFTY_500"
        tables = pd.read_html(wiki)
        if tables:
            # pick the largest table (most rows)
            df = max(tables, key=lambda t: t.shape[0])
            cols = [str(c).strip().lower() for c in df.columns]
            # look for likely column
            for candidate in ("symbol", "ticker", "ticker symbol", "code", "scrip"):
                if candidate in cols:
                    sym_col = df.columns[cols.index(candidate)]
                    syms = df[sym_col].dropna().astype(str).str.strip().tolist()
                    syms = [s + ("" if s.endswith(".NS") else ".NS") for s in syms if s]
                    if syms:
                        return syms
    except Exception:
        pass

    # 3) fallback small list
    fallback = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS"
    ]
    return fallback


@st.cache_data(ttl=60 * 5)
def fetch_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Download price history, normalize columns, return dataframe with standard OHLCV columns."""
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, threads=False)
        # sometimes empty or MultiIndex columns — normalize
        if df is None or df.empty:
            # try ticker.history fallback
            t = yf.Ticker(symbol)
            df = t.history(period=period, interval=interval)
            if df is None or df.empty:
                return pd.DataFrame()
        # flatten multiindex columns if any
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join([str(x) for x in col if x is not None]).strip() for col in df.columns.values]
        # normalize names to standard ones
        cols_map = {}
        for c in df.columns:
            cl = str(c).lower()
            if "open" in cl and "adj" not in cl:
                cols_map[c] = "Open"
            elif "high" in cl:
                cols_map[c] = "High"
            elif "low" in cl and "adj" not in cl:
                cols_map[c] = "Low"
            elif "adj" in cl and "close" in cl:
                cols_map[c] = "Adj Close"
            elif "close" in cl:
                cols_map[c] = "Close"
            elif "volume" in cl:
                cols_map[c] = "Volume"
            else:
                cols_map[c] = c
        df = df.rename(columns=cols_map)
        # ensure required columns exist
        for req in ("Open", "High", "Low", "Close"):
            if req not in df.columns:
                return pd.DataFrame()
        df = df.reset_index()
        # ensure datetime index column name 'Date' or 'ts'
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60 * 60)
def fetch_company_info(symbol: str) -> dict:
    """Return Ticker.info with safe fallback."""
    try:
        t = yf.Ticker(symbol)
        info = {}
        try:
            info = t.get_info() if hasattr(t, "get_info") else t.info
        except Exception:
            # older yfinance exposes .info
            info = getattr(t, "info", {}) or {}
        # some quick important fields (safe)
        quick = {
            "shortName": info.get("shortName") or info.get("longName"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "marketCap": info.get("ma
