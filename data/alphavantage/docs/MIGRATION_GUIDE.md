# Migration Guide - Alpha Vantage Restructure

## 🔄 What Changed?

The Alpha Vantage module has been restructured for better organization and scalability.

### Old Structure (Deprecated)
```
data/alphavantage/
├── download_intraday.py  ❌ REMOVED
├── test_intraday.py      ❌ REMOVED
├── INTRADAY_GUIDE.md     ❌ REMOVED
└── load_env.sh           ❌ REMOVED
```

### New Structure (Current)
```
data/alphavantage/
├── core/              ✅ Shared utilities
│   ├── __init__.py
│   └── api_client.py
├── equities/          ✅ Stock data
│   ├── __init__.py
│   ├── intraday.py   (improved with more parameters)
│   └── daily.py
├── options/           ✅ Options data
│   ├── __init__.py
│   └── historical.py (with Greeks + IV)
├── docs/              ✅ Documentation
│   └── MIGRATION_GUIDE.md
└── README.md          ✅ Complete guide
```

## 📝 Command Updates

### Intraday Data

**Old:**
```bash
python -m data.alphavantage.download_intraday --symbol SPY --interval 1min
```

**New:**
```bash
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min
```

### New Features in Intraday

```bash
# Historical month (20+ years available!)
python -m data.alphavantage.equities.intraday --symbol AAPL --interval 5min --month 2020-01

# Regular hours only (no pre/post market)
python -m data.alphavantage.equities.intraday --symbol SPY --no-extended-hours

# Raw prices (not adjusted)
python -m data.alphavantage.equities.intraday --symbol AAPL --no-adjusted
```

### Options (NEW!)

```bash
# Latest options chain
python -m data.alphavantage.options.historical --symbol AAPL

# Specific date
python -m data.alphavantage.options.historical --symbol SPY --date 2025-10-15

# Multiple symbols
python -m data.alphavantage.options.historical --symbols AAPL MSFT TSLA
```

## 🐍 Python API Updates

### Old Import

```python
from data.alphavantage.download_intraday import (
    fetch_intraday_data,
    download_symbol_intraday
)
```

### New Import (Multiple Options)

```python
# Option 1: From main module
from data.alphavantage import (
    fetch_intraday_data,
    download_symbol_intraday,
    fetch_historical_options,
    download_options_for_symbol
)

# Option 2: From specific submodule
from data.alphavantage.equities import (
    fetch_intraday_data,
    download_symbol_intraday
)

from data.alphavantage.options import (
    fetch_historical_options,
    download_options_for_symbol
)

# Option 3: Direct import
from data.alphavantage.equities.intraday import fetch_intraday_data
from data.alphavantage.options.historical import fetch_historical_options
```

## ✨ New Features

### 1. Historical Month Parameter (Intraday)

```python
# Download specific historical month
df, err = fetch_intraday_data('SPY', '1min', month='2020-01')
```

Can access **20+ years** of data (from 2000-01)!

### 2. Extended Hours Control (Intraday)

```python
# Include pre/post market (4am-8pm ET) - DEFAULT
df, err = fetch_intraday_data('SPY', '1min', extended_hours=True)

# Regular hours only (9:30am-4pm ET)
df, err = fetch_intraday_data('SPY', '1min', extended_hours=False)
```

### 3. Adjusted Prices Control (Intraday)

```python
# Adjusted for splits/dividends - DEFAULT
df, err = fetch_intraday_data('AAPL', '1min', adjusted=True)

# Raw prices
df, err = fetch_intraday_data('AAPL', '1min', adjusted=False)
```

### 4. Options Historical Data (NEW!)

```python
# Get latest options chain with Greeks and IV
df, err = fetch_historical_options('AAPL')

# Specific date
df, err = fetch_historical_options('AAPL', date='2025-10-15')

# Download to database
inserted, updated, err = download_options_for_symbol('AAPL')
```

Returns:
- Pricing: last, mark, bid/ask with sizes
- Greeks: delta, gamma, theta, vega, rho
- Implied Volatility
- Volume & Open Interest

## 💾 Database Changes

### New Table: options_data_historical

```sql
-- Query options chain
SELECT * FROM get_option_chain('AAPL', '2025-10-15');

-- Options summary
SELECT * FROM get_options_summary('AAPL', '2025-10-15');

-- Coverage
SELECT * FROM options_data_coverage;
```

### Existing Table: market_data_intraday (unchanged)

All your existing intraday data is preserved.

## 🔧 Migration Steps

### For Scripts

1. Update import statements (see above)
2. Update module paths in commands
3. Optional: Use new parameters (month, extended_hours, adjusted)

### For Database

No migration needed! All existing data is preserved.

New options table created automatically:
```bash
# Already applied during restructure
# infrastructure/database/init-scripts/03_options_data_schema.sql
```

## ✅ Checklist

- [ ] Update import statements in your code
- [ ] Update command-line scripts/cron jobs
- [ ] Test new module paths work
- [ ] Explore new features (month parameter, options data)
- [ ] Read new README.md for full documentation

## 📚 Resources

- **Main README**: `data/alphavantage/README.md` (comprehensive guide)
- **Code**: Well-documented with docstrings
- **SQL Schema**: `infrastructure/database/init-scripts/03_options_data_schema.sql`

## 🎉 Benefits

1. **Better Organization**: Separate modules for equities vs options
2. **More Features**: Historical months, extended hours control, options with Greeks
3. **Cleaner Code**: Shared utilities in `core/`
4. **Production Ready**: Options data with 15+ years of history
5. **Better Documentation**: Comprehensive guides and examples

## 💡 Questions?

Check the main README or code docstrings - everything is documented!

