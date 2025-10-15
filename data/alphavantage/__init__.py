"""
Alpha Vantage Data Providers.

This module provides data downloaders for Alpha Vantage API.

Modules:
- core: Shared API client and utilities
- equities: Stock intraday and daily data
- options: Historical options with Greeks and IV

Features:
- Professional-grade rate limiting (5 calls/min, 25 calls/day)
- Incremental downloads (only new data)
- Interactive and CLI modes
- Direct database integration (TimescaleDB)
- Comprehensive error handling

Setup:
1. Get free API key from https://www.alphavantage.co/support/#api-key
2. Set environment variable: export ALPHAVANTAGE_API_KEY=your_key_here
3. Or add to .env.local: ALPHAVANTAGE_API_KEY=your_key_here

Example Usage:
    # Equities intraday
    python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min
    
    # Options historical
    python -m data.alphavantage.options.historical --symbol AAPL
    
    # Interactive mode (recommended)
    python -m data.alphavantage.equities.intraday
    python -m data.alphavantage.options.historical
"""

from data.alphavantage.core import (
    make_api_request,
    get_api_key,
    enforce_rate_limit,
)

from data.alphavantage.equities import (
    fetch_intraday_data,
    download_symbol_intraday,
    download_multiple_symbols,
)

from data.alphavantage.options import (
    fetch_historical_options,
    download_options_for_symbol,
    download_options_for_multiple_symbols,
)

__all__ = [
    # Core
    'make_api_request',
    'get_api_key',
    'enforce_rate_limit',
    
    # Equities
    'fetch_intraday_data',
    'download_symbol_intraday',
    'download_multiple_symbols',
    
    # Options
    'fetch_historical_options',
    'download_options_for_symbol',
    'download_options_for_multiple_symbols',
]

__version__ = '1.0.0'
