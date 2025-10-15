"""
yfinance data provider module.

This module contains all code for downloading and managing data from Yahoo Finance
using the yfinance library.

Available modules:
- download_sp500_yfinance: Download S&P 500 constituents and historical data
- download_indices: Download benchmark indices (SPY, QQQ, etc.)
- add_tickers: Add custom tickers to the database
- update_daily: Daily update script for all data
- download_benchmarks_historical: Historical benchmark data downloader
- test_download: Test data download functionality

Note: yfinance has aggressive rate limits. Use with caution and consider
switching to Alpha Vantage or Polygon.io for production use.
"""

from data.yfinance.download_sp500_yfinance import (
    download_symbol_data,
    download_all_sp500,
    update_sp500_constituents,
    fetch_sp500_constituents,
)

from data.yfinance.download_indices import (
    download_index_data,
    download_all_indices,
    get_active_indices,
    update_indices_daily,
)

from data.yfinance.add_tickers import (
    add_tickers,
    check_ticker_exists,
    get_ticker_info,
)

__all__ = [
    # SP500 functions
    'download_symbol_data',
    'download_all_sp500',
    'update_sp500_constituents',
    'fetch_sp500_constituents',
    
    # Indices functions
    'download_index_data',
    'download_all_indices',
    'get_active_indices',
    'update_indices_daily',
    
    # Custom tickers
    'add_tickers',
    'check_ticker_exists',
    'get_ticker_info',
]

