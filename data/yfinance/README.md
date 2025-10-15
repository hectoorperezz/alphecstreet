# yfinance Data Provider

**Status**: ✅ Active (recommended for daily data only)

This module provides daily OHLCV data from Yahoo Finance. For intraday data and options, use [`../alphavantage/`](../alphavantage/).

---

## ⚠️ Important: Rate Limits

Yahoo Finance has aggressive rate limiting (2024-2025):
- ~2-5 requests per minute maximum
- Sequential requests often trigger blocking
- New IPs still get rate limited

**Best Practice**: Use yfinance for daily data, Alpha Vantage for intraday/options.

---

## 🚀 Quick Start

```bash
# Download S&P 500 historical data
python -m data.yfinance.download_sp500_yfinance --start-date 2020-01-01

# Download benchmark indices (SPY, QQQ, etc.)
python -m data.yfinance.download_indices --start-date 2020-01-01

# Add custom tickers
python -m data.yfinance.add_tickers --tickers AAPL MSFT TSLA

# Daily update (all data)
python -m data.yfinance.update_daily
```

---

## 📁 Available Modules

| Module | Purpose | Usage |
|--------|---------|-------|
| `download_sp500_yfinance.py` | S&P 500 constituents & history | `python -m data.yfinance.download_sp500_yfinance` |
| `download_indices.py` | Benchmark indices (17 indices) | `python -m data.yfinance.download_indices` |
| `add_tickers.py` | Add custom tickers | `python -m data.yfinance.add_tickers --tickers AAPL` |
| `update_daily.py` | Daily incremental updates | `python -m data.yfinance.update_daily` |

---

## 📊 S&P 500 Data

### Download Historical Data

```bash
# All constituents from 2020
python -m data.yfinance.download_sp500_yfinance --start-date 2020-01-01

# Single symbol
python -m data.yfinance.download_sp500_yfinance --symbol AAPL --start-date 2020-01-01

# Custom date range
python -m data.yfinance.download_sp500_yfinance --start-date 2020-01-01 --end-date 2023-12-31

# Skip symbols with existing data
python -m data.yfinance.download_sp500_yfinance --skip-existing --start-date 2020-01-01
```

### Update S&P 500 Constituents

```bash
# Refresh list from Wikipedia
python -m data.yfinance.download_sp500_yfinance --update-constituents
```

### Features

✅ **Incremental Downloads** - Only new data, no duplicates  
✅ **Automatic Retries** - Handles transient errors  
✅ **Sector Tracking** - Stores sector/industry info  
✅ **Delisting Handling** - Marks inactive constituents  
✅ **TimescaleDB Integration** - Stores in `market_data_daily`  

---

## 📈 Benchmark Indices

### Available Indices (17 total)

**Equity Indices:**
- **SPY** - S&P 500 ETF
- **QQQ** - NASDAQ-100 ETF
- **DIA** - Dow Jones ETF
- **IWM** - Russell 2000 (Small Caps)
- **VTI** - Vanguard Total Stock Market
- **^GSPC** - S&P 500 Index
- **^IXIC** - NASDAQ Composite
- **^DJI** - Dow Jones Industrial

**Sector ETFs:**
- **XLK** - Technology
- **XLF** - Financial
- **XLE** - Energy

**International:**
- **EFA** - Developed Markets (ex-US)
- **EEM** - Emerging Markets

**Bonds:**
- **AGG** - US Aggregate Bonds
- **TLT** - 20+ Year Treasury

**Commodities:**
- **GLD** - Gold

**Volatility:**
- **^VIX** - CBOE Volatility Index

### Download Indices

```bash
# All indices (full history)
python -m data.yfinance.download_indices --start-date 2015-01-01

# Daily update (last 7 days only - FAST)
python -m data.yfinance.download_indices --daily-update

# Specific index
python -m data.yfinance.download_indices --symbol SPY --start-date 2020-01-01
```

### Compare with Benchmarks

```python
from data.database import query_to_dataframe

# Compare NVDA vs SPY (SQL function)
comparison = query_to_dataframe("""
    SELECT * FROM compare_to_benchmark(
        'NVDA',           -- Your stock
        'SPY',            -- Benchmark
        '2024-01-01',     -- Start date
        '2024-12-31'      -- End date
    )
    ORDER BY date
""")

# Results
print(f"NVDA return: {comparison['stock_cumulative_pct'].iloc[-1]:.2f}%")
print(f"SPY return: {comparison['benchmark_cumulative_pct'].iloc[-1]:.2f}%")
print(f"Alpha: {comparison['stock_cumulative_pct'].iloc[-1] - comparison['benchmark_cumulative_pct'].iloc[-1]:.2f}%")

# Visualize
import matplotlib.pyplot as plt
plt.plot(comparison['date'], comparison['stock_cumulative_pct'], label='NVDA')
plt.plot(comparison['date'], comparison['benchmark_cumulative_pct'], label='SPY')
plt.legend()
plt.show()
```

---

## ➕ Add Custom Tickers

### Interactive Mode (Recommended)

```bash
python -m data.yfinance.add_tickers
```

Prompts for:
- Ticker symbols (e.g., `AAPL MSFT TSLA`)
- Start date (default: 2015-01-01)
- End date (default: today)

### Command Line Mode

```bash
# Single ticker
python -m data.yfinance.add_tickers --tickers AAPL

# Multiple tickers
python -m data.yfinance.add_tickers --tickers AAPL MSFT GOOGL TSLA

# Custom date range
python -m data.yfinance.add_tickers --tickers AAPL --start-date 2020-01-01 --end-date 2025-01-01

# Force re-download (ignore existing)
python -m data.yfinance.add_tickers --tickers AAPL --force
```

### Smart Features

✅ **Duplicate Detection** - Checks if ticker exists  
✅ **Incremental Updates** - Only downloads new data  
✅ **Interactive Prompts** - Asks before updating existing data  
✅ **Batch Support** - Multiple tickers at once  

### Supported Ticker Types

- **US Stocks**: AAPL, MSFT, GOOGL
- **ETFs**: SPY, QQQ, VTI
- **Indices**: ^GSPC, ^DJI, ^IXIC
- **International**: ASML, TSM, BABA
- **Crypto**: BTC-USD, ETH-USD
- **Commodities**: GC=F (Gold), CL=F (Oil)

### Examples

```bash
# Add tech stocks
python -m data.yfinance.add_tickers --tickers AAPL MSFT GOOGL AMZN META NVDA

# Add sector ETFs
python -m data.yfinance.add_tickers --tickers XLK XLF XLE XLV XLI XLP

# Add crypto
python -m data.yfinance.add_tickers --tickers BTC-USD ETH-USD

# Add international
python -m data.yfinance.add_tickers --tickers EWJ EWG EWU EWZ
```

---

## 🔄 Daily Updates

### Automatic Updates

```bash
# Update all S&P 500 stocks + indices
python -m data.yfinance.update_daily

# Only last 5 days (faster)
python -m data.yfinance.update_daily --days-back 5

# With custom date range
python -m data.yfinance.update_daily --days-back 30
```

### Cron Job Setup

```bash
# Edit crontab
crontab -e

# Add this line (daily at 6 PM)
0 18 * * * cd /path/to/alphecstreet && python -m data.yfinance.update_daily >> /tmp/market_update.log 2>&1
```

---

## 🐍 Python API

```python
from data.yfinance.download_sp500_yfinance import download_symbol_data
from data.yfinance.add_tickers import add_tickers
from data.database import query_to_dataframe

# Download single symbol
bars, error = download_symbol_data(
    symbol='AAPL',
    start_date='2020-01-01',
    skip_existing=True  # Incremental download
)

# Add multiple tickers
stats = add_tickers(
    tickers=['AAPL', 'MSFT', 'GOOGL'],
    start_date='2020-01-01',
    force=False  # Don't re-download existing
)

print(f"New: {stats['new']}, Updated: {stats['updated']}")

# Query data
df = query_to_dataframe("""
    SELECT * FROM market_data_daily
    WHERE symbol = 'AAPL'
    AND time >= '2024-01-01'
    ORDER BY time
""")
```

---

## 📊 Database Schema

Data is stored in `market_data_daily` (TimescaleDB hypertable):

```sql
CREATE TABLE market_data_daily (
    "time" DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(18, 6),
    high DECIMAL(18, 6),
    low DECIMAL(18, 6),
    close DECIMAL(18, 6),
    adj_close DECIMAL(18, 6),
    volume BIGINT,
    PRIMARY KEY ("time", symbol)
);
```

**Features:**
- ✅ Hypertable (optimized for time-series)
- ✅ Auto-compression (data > 30 days)
- ✅ Monthly partitioning
- ✅ Continuous aggregates (weekly, monthly)

**Views:**
- `latest_prices` - Most recent price per symbol
- `data_coverage` - Date ranges per symbol
- `sector_summary` - Aggregates by sector

---

## ⚡ Performance Tips

1. **Incremental Downloads**: Always use `--skip-existing` or `skip_existing=True`
2. **Batch Size**: Download 5-10 symbols at a time to avoid rate limits
3. **Daily Updates**: Use `update_daily.py` instead of re-downloading
4. **Start Recent**: Use `--start-date 2020-01-01` for faster initial loads
5. **Avoid --force**: Only re-download when absolutely necessary

---

## ❌ Known Issues

1. **Rate Limits**: Very aggressive, even with delays
2. **Incomplete Data**: Some tickers return partial data
3. **Session Errors**: Occasional timeout issues
4. **No Intraday**: Only daily EOD data (use Alpha Vantage for intraday)
5. **Index Symbols**: Symbols with `^` may have limited data

---

## 🔧 Troubleshooting

### Rate Limit Errors

```
⚠️ Rate limited, waiting 10s before retry...
```

**Solution**: Wait a few minutes. The script has automatic retry logic.

### No Data Found

```
❌ No data found for XYZ
```

**Possible reasons**:
- Incorrect ticker symbol
- Recently delisted stock
- Not available on Yahoo Finance

**Solution**: Verify on [finance.yahoo.com](https://finance.yahoo.com)

### Database Connection Error

```bash
# Check if Docker is running
docker ps | grep timescaledb

# Restart if needed
cd infrastructure/database
docker-compose restart
```

---

## 🚀 Migration to Alpha Vantage

For better reliability and intraday data:

```bash
# Use Alpha Vantage instead
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min
python -m data.alphavantage.options.historical --symbol AAPL
```

See [`../alphavantage/README.md`](../alphavantage/README.md) for details.

---

## 📚 Complete Examples

### Example 1: Build Custom Universe

```python
from data.yfinance.add_tickers import add_tickers

# My tech watchlist
tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 
               'NVDA', 'TSLA', 'AMD', 'INTC', 'CRM']

stats = add_tickers(
    tickers=tech_stocks,
    start_date='2020-01-01',
    force=False
)

print(f"✅ Added {stats['new']} new tickers")
print(f"🔄 Updated {stats['updated']} existing tickers")
```

### Example 2: Sector Analysis

```python
from data.database import query_to_dataframe

# Get all tech sector stocks
tech_stocks = query_to_dataframe("""
    SELECT DISTINCT m.symbol, c.company_name
    FROM market_data_daily m
    JOIN sp500_constituents c ON m.symbol = c.symbol
    WHERE c.sector = 'Information Technology'
    AND c.is_active = TRUE
    ORDER BY m.symbol
""")

# Calculate sector performance
sector_perf = query_to_dataframe("""
    SELECT 
        symbol,
        ((last.adj_close - first.adj_close) / first.adj_close * 100) as ytd_return
    FROM 
        (SELECT symbol, adj_close FROM market_data_daily 
         WHERE time = '2024-01-01') first
    JOIN
        (SELECT symbol, adj_close FROM market_data_daily 
         WHERE time = CURRENT_DATE - 1) last
    USING (symbol)
    ORDER BY ytd_return DESC
""")

print(sector_perf.head(10))
```

### Example 3: Correlation Matrix

```python
import pandas as pd
from data.database import query_to_dataframe

symbols = ['AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ']
returns_df = pd.DataFrame()

for symbol in symbols:
    df = query_to_dataframe(f"""
        SELECT 
            time,
            (close - LAG(close) OVER (ORDER BY time)) / 
                LAG(close) OVER (ORDER BY time) as return
        FROM market_data_daily
        WHERE symbol = '{symbol}' 
        AND time >= '2024-01-01'
    """)
    returns_df[symbol] = df.set_index('time')['return']

# Correlation matrix
corr = returns_df.corr()
print(corr)

# Visualize
import seaborn as sns
sns.heatmap(corr, annot=True, cmap='coolwarm')
```

---

## 💡 Best Practices

1. ✅ Use incremental downloads (`skip_existing=True`)
2. ✅ Update daily with `update_daily.py`
3. ✅ Compare strategies vs benchmarks (SPY, QQQ)
4. ✅ Store only what you need (limit date range)
5. ✅ Monitor download logs for errors
6. ✅ Use Alpha Vantage for intraday/options data
7. ✅ Back up database regularly

---

## 📞 Support

- **Documentation**: This README
- **Database Schema**: `infrastructure/database/init-scripts/01_market_data_schema.sql`
- **Alpha Vantage**: For intraday/options → `../alphavantage/README.md`
- **Main Guide**: `../README.md`

---

**Need intraday data or options?** → Use [Alpha Vantage](../alphavantage/README.md) instead! 🚀
