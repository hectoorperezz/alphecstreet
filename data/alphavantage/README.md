# Alpha Vantage Data Providers

Professional-grade data downloaders for Alpha Vantage API with TimescaleDB integration.

## 🎯 Overview

This module provides comprehensive access to Alpha Vantage financial data:

- **Equities**: Intraday OHLCV (1min to 60min) with 20+ years of history
- **Options**: Historical option chains with Greeks and IV from 2008

All data is stored in TimescaleDB with automatic compression, incremental updates, and production-ready infrastructure.

## 📦 Structure

```
alphavantage/
├── core/              # Shared API client and utilities
│   ├── __init__.py
│   └── api_client.py  # Rate limiting, error handling
├── equities/          # Stock data
│   ├── __init__.py
│   ├── intraday.py    # 1min-60min OHLCV (✅ IMPLEMENTED)
│   └── daily.py       # Daily data (placeholder - use yfinance)
├── options/           # Options data
│   ├── __init__.py
│   └── historical.py  # Historical chains + Greeks + IV (✅ IMPLEMENTED)
└── docs/              # Documentation
```

## 🚀 Quick Start

### 1. Setup

Get a free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key)

```bash
# Option 1: Environment variable
export ALPHAVANTAGE_API_KEY=your_key_here

# Option 2: Add to .env.local
echo "ALPHAVANTAGE_API_KEY=your_key_here" >> .env.local
source data/alphavantage/load_env.sh
```

### 2. Download Data

**Equities Intraday (Interactive Mode)**
```bash
python -m data.alphavantage.equities.intraday
# Prompts for: symbol, interval, adjusted, extended_hours, month
```

**Options Historical (Interactive Mode)**
```bash
python -m data.alphavantage.options.historical
# Prompts for: symbol, date
```

**Command Line Mode**
```bash
# Intraday - last 30 days
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min

# Intraday - specific historical month
python -m data.alphavantage.equities.intraday --symbol AAPL --interval 5min --month 2020-01

# Options - latest chain
python -m data.alphavantage.options.historical --symbol AAPL

# Options - specific date
python -m data.alphavantage.options.historical --symbol SPY --date 2025-10-15
```

## 📊 Data Coverage

### Equities Intraday
- **Intervals**: 1min, 5min, 15min, 30min, 60min
- **History**: 20+ years (with `--month` parameter, from 2000-01)
- **Features**: 
  - Adjusted for splits/dividends
  - Extended hours (4am-8pm ET)
  - Regular hours only option (9:30am-4pm ET)
- **Table**: `market_data_intraday`

### Options Historical
- **History**: 15+ years (from 2008-01-01)
- **Includes**:
  - Pricing: last, mark, bid/ask with sizes
  - Greeks: delta, gamma, theta, vega, rho
  - Implied Volatility (IV)
  - Volume & Open Interest
- **Table**: `options_data_historical`

## 🔧 Features

### ✅ Implemented

1. **Professional Rate Limiting**
   - Free tier: 25 calls/day, 5 calls/minute
   - Auto-delays between requests (15 seconds)
   - Respects API limits

2. **Incremental Downloads**
   - Checks existing data before download
   - Only fetches new bars
   - Prevents duplicate data

3. **Interactive Mode**
   - User-friendly prompts
   - No need to remember command-line flags
   - Input validation

4. **TimescaleDB Integration**
   - Hypertables with automatic partitioning
   - Compression after 7-30 days
   - Optimized indexes
   - Fast queries

5. **Error Handling**
   - API errors caught and reported
   - Network timeout protection
   - Data validation

6. **Database Views & Functions**
   - Latest prices
   - Data coverage summaries
   - Option chain queries
   - Options summary stats

## 📋 API Limits

**Free Tier:**
- 25 API calls per day
- 5 API calls per minute

**Our Protection:**
- 15-second delays between calls
- Automatic rate limiting
- Clear error messages if limit exceeded

**Tips:**
- Download historical data using `--month` parameter (1 call per month)
- Use yfinance for daily data (unlimited)
- Reserve Alpha Vantage for intraday and options

## 📚 Detailed Guides

### Equities Intraday

**All Available Parameters:**
```bash
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --interval 1min \
  --month 2020-01 \
  --no-adjusted \
  --no-extended-hours
```

**Parameter Reference:**
- `--symbol`: Single ticker (e.g., SPY, AAPL)
- `--symbols`: Multiple tickers (space-separated)
- `--interval`: 1min, 5min, 15min, 30min, or 60min
- `--month`: Historical month YYYY-MM (from 2000-01)
- `--no-adjusted`: Raw prices (not adjusted for splits/dividends)
- `--no-extended-hours`: Regular market hours only (9:30am-4pm ET)

**Examples:**

```bash
# Recent 1-minute data (last 30 days)
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min

# Historical month (can download 20+ years)
python -m data.alphavantage.equities.intraday --symbol AAPL --interval 5min --month 2015-06

# Multiple symbols
python -m data.alphavantage.equities.intraday --symbols SPY QQQ IWM --interval 1min

# Extended hours data
python -m data.alphavantage.equities.intraday --symbol TSLA --interval 1min
# Includes 4:00am-9:30am (pre-market) and 4:00pm-8:00pm (post-market)

# Regular hours only
python -m data.alphavantage.equities.intraday --symbol AAPL --no-extended-hours
# Only 9:30am-4:00pm ET
```

### Options Historical

**All Available Parameters:**
```bash
python -m data.alphavantage.options.historical \
  --symbol AAPL \
  --date 2025-10-15
```

**Parameter Reference:**
- `--symbol`: Single ticker
- `--symbols`: Multiple tickers (space-separated)
- `--date`: Specific date YYYY-MM-DD (from 2008-01-01)

**Examples:**

```bash
# Latest options chain
python -m data.alphavantage.options.historical --symbol AAPL

# Specific historical date
python -m data.alphavantage.options.historical --symbol SPY --date 2024-12-20

# Multiple symbols
python -m data.alphavantage.options.historical --symbols AAPL MSFT TSLA
```

## 💾 Database Schema

### Intraday Data

**Table**: `market_data_intraday`

```sql
SELECT * FROM market_data_intraday
WHERE symbol = 'SPY' AND interval = '1min'
LIMIT 10;
```

**Columns:**
- `time`: Timestamp with timezone
- `symbol`: Stock symbol
- `interval`: 1min, 5min, 15min, 30min, 60min
- `open, high, low, close`: OHLC prices
- `volume`: Trading volume
- `data_source`: 'alphavantage'

**Views:**
- `latest_intraday_prices`: Most recent prices per symbol/interval
- `intraday_data_coverage`: Summary of available data

**Continuous Aggregate:**
- `market_data_hourly`: Automatically aggregated hourly bars

### Options Data

**Table**: `options_data_historical`

```sql
SELECT * FROM get_option_chain('AAPL', '2025-10-15');
```

**Columns:**
- Contract: `contract_id, symbol, expiration, strike, type`
- Pricing: `last, mark, bid, ask, bid_size, ask_size`
- Volume: `volume, open_interest`
- Greeks: `delta, gamma, theta, vega, rho`
- Volatility: `implied_volatility`

**Views:**
- `latest_options_chain`: Most recent chain for each contract
- `options_data_coverage`: Summary of available options data

**Functions:**
- `get_option_chain(symbol, date, exp_min, exp_max, type)`: Query chains
- `get_options_summary(symbol, date)`: Summary statistics

## 🐍 Python API

```python
from data.alphavantage import (
    # Equities
    fetch_intraday_data,
    download_symbol_intraday,
    download_multiple_symbols,
    
    # Options
    fetch_historical_options,
    download_options_for_symbol,
    download_options_for_multiple_symbols,
)

# Fetch intraday data
df, error = fetch_intraday_data('SPY', interval='1min', adjusted=True, extended_hours=True)

# Download and save to database
inserted, updated, error = download_symbol_intraday('SPY', '1min')

# Fetch options
df, error = fetch_historical_options('AAPL', date='2025-10-15')

# Download options to database
inserted, updated, error = download_options_for_symbol('AAPL')
```

## 🔍 Query Examples

### Intraday Queries

```sql
-- Latest intraday prices
SELECT * FROM latest_intraday_prices;

-- Specific symbol/interval coverage
SELECT * FROM intraday_data_coverage WHERE symbol = 'SPY';

-- Get bars for specific timeframe
SELECT * FROM get_intraday_bars('SPY', '1min', '2025-10-01', '2025-10-10');

-- Intraday statistics
SELECT * FROM get_intraday_stats('SPY', '1min', '2025-10-01', '2025-10-10');

-- Hourly aggregate
SELECT * FROM market_data_hourly WHERE symbol = 'SPY' LIMIT 100;
```

### Options Queries

```sql
-- Latest options chain
SELECT * FROM latest_options_chain WHERE symbol = 'AAPL';

-- Options coverage
SELECT * FROM options_data_coverage;

-- Get specific option chain
SELECT * FROM get_option_chain('AAPL', '2025-10-15');

-- Filter by expiration
SELECT * FROM get_option_chain('AAPL', '2025-10-15', '2025-11-01', '2025-12-31');

-- Only calls
SELECT * FROM get_option_chain('AAPL', '2025-10-15', NULL, NULL, 'call');

-- Summary statistics
SELECT * FROM get_options_summary('AAPL', '2025-10-15');

-- Find high IV options
SELECT contract_id, strike, type, implied_volatility
FROM options_data_historical
WHERE symbol = 'AAPL' AND date = '2025-10-15' AND implied_volatility > 0.5
ORDER BY implied_volatility DESC;
```

## 🧪 Testing

```bash
# Test intraday integration
python data/alphavantage/test_intraday.py

# Test in Python
from data.database import query_to_dataframe

# Check intraday data
df = query_to_dataframe("SELECT * FROM intraday_data_coverage")
print(df)

# Check options data
df = query_to_dataframe("SELECT * FROM options_data_coverage")
print(df)
```

## ⚠️ Important Notes

1. **API Limits**: Free tier is 25 calls/day. Plan downloads carefully.

2. **Historical Data**: Use `--month` parameter to download years of history
   - Each month = 1 API call
   - Can download from 2000-01 to present

3. **Daily Data**: For daily OHLCV, use yfinance (no API limits)
   ```bash
   python -m data.yfinance.download_sp500_yfinance
   ```

4. **Extended Hours**: By default includes pre/post market (4am-8pm ET)
   - Use `--no-extended-hours` for regular hours only (9:30am-4pm)

5. **Adjusted Prices**: Default is adjusted for splits/dividends
   - Use `--no-adjusted` for raw prices

6. **Incremental Updates**: Running same command twice won't re-download
   - Only fetches new data since last download
   - Safe to run daily for updates

## 🔄 Recommended Workflow

### Initial Setup (One-time)

```bash
# 1. Download SPY intraday data for last few years
# (Download month by month to stay under daily API limit)
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min --month 2025-09
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min --month 2025-08
# ... continue for desired history (25 months max per day)

# 2. Download initial options chain
python -m data.alphavantage.options.historical --symbol SPY
```

### Daily Updates

```bash
# Update intraday (fetches only new data)
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min

# Update options chain
python -m data.alphavantage.options.historical --symbol SPY
```

### Strategy Development

```python
from data.database import query_to_dataframe

# Load intraday data for backtesting
df = query_to_dataframe("""
    SELECT * FROM market_data_intraday
    WHERE symbol = 'SPY' AND interval = '5min'
    ORDER BY time
""")

# Load options for strategy
df = query_to_dataframe("""
    SELECT * FROM get_option_chain('SPY', CURRENT_DATE - 1)
""")
```

## 📞 Support

**Documentation:**
- This README
- Code docstrings (comprehensive)
- SQL schema comments

**Troubleshooting:**
- Check API key: `echo $ALPHAVANTAGE_API_KEY`
- View database logs: `docker logs alphecstreet_timescaledb`
- Test connection: `python data/alphavantage/test_intraday.py`

**Common Issues:**
1. "API key not found" → Set environment variable
2. "Rate limited" → Wait for API limits to reset (next day)
3. "No data returned" → Check symbol spelling and date availability

## 📊 Current Status

### ✅ Production Ready
- Equities intraday (1min to 60min)
- Options historical (with Greeks + IV)
- Rate limiting
- Incremental updates
- Database integration
- Documentation

### 🚧 Future Enhancements
- Equities daily downloader (currently use yfinance)
- Real-time data streaming
- Automated daily cron jobs
- Premium tier support (higher limits)
- Additional Alpha Vantage endpoints

## 🎉 Success!

You now have professional-grade access to:
- **20+ years** of intraday stock data
- **15+ years** of options data with Greeks
- All stored in production-ready TimescaleDB
- Interactive and automated workflows
- Comprehensive documentation

Happy trading! 🚀
