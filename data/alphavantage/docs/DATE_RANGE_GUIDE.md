# Date Range Download Guide

## 🎯 Overview

The date range download feature allows you to automatically download years of historical intraday data by breaking the request into monthly batches. This is essential for backtesting strategies that require extensive historical data.

## 🚀 Quick Start

### Interactive Mode (Easiest)

```bash
python -m data.alphavantage.equities.intraday
```

Then select option 3 (Date range) and follow the prompts.

### Command Line Mode

```bash
# Download SPY 1-minute data from 2020 to 2025
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2020-01 \
  --end-date 2025-10 \
  --interval 1min

# Multiple symbols
python -m data.alphavantage.equities.intraday \
  --symbols SPY QQQ IWM \
  --start-date 2024-01 \
  --end-date 2024-12 \
  --interval 5min
```

## 📊 How It Works

1. **Month Generation**: Automatically generates list of months between start and end dates
2. **Sequential Download**: Downloads each month one-by-one (respects rate limits)
3. **Progress Tracking**: Shows real-time progress and estimated completion time
4. **Error Handling**: Continues downloading even if individual months fail
5. **Database Storage**: Automatically stores all data in TimescaleDB

## ⏱️ Time Estimates

The free tier allows:
- **25 API calls per day**
- **5 API calls per minute**

With 15-second delays between calls:
- 1 month = ~15 seconds
- 1 year (12 months) = ~3 minutes
- 5 years (60 months) = ~15 minutes
- 10 years (120 months) = ~30 minutes

**Important**: 25 months = 25 API calls (daily limit for free tier)

## 💡 Examples

### Example 1: Single Symbol, 1 Year

```bash
python -m data.alphavantage.equities.intraday \
  --symbol AAPL \
  --start-date 2024-01 \
  --end-date 2024-12 \
  --interval 1min
```

- **Months**: 12
- **API Calls**: 12
- **Time**: ~3 minutes
- **Within free tier**: ✅ Yes

### Example 2: Single Symbol, 5 Years

```bash
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2020-01 \
  --end-date 2024-12 \
  --interval 5min
```

- **Months**: 60
- **API Calls**: 60
- **Time**: ~15 minutes
- **Within free tier**: ⚠️ No (requires 3 days or premium key)

### Example 3: Multiple Symbols, 1 Year

```bash
python -m data.alphavantage.equities.intraday \
  --symbols SPY QQQ IWM \
  --start-date 2024-01 \
  --end-date 2024-12 \
  --interval 1min
```

- **Months per symbol**: 12
- **Total API Calls**: 36 (3 symbols × 12 months)
- **Time**: ~9 minutes
- **Within free tier**: ⚠️ No (requires 2 days or premium key)

### Example 4: Aggressive - 15 Years of Data

```bash
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2010-01 \
  --end-date 2025-10 \
  --interval 1min
```

- **Months**: 190
- **API Calls**: 190
- **Time**: ~48 minutes
- **Within free tier**: ⚠️ No (requires 8 days or premium key)

## 📋 Planning Your Download

### Calculate API Calls Needed

```
API Calls = Number of Symbols × Number of Months
```

### Calculate Number of Months

```python
from datetime import datetime
from dateutil.relativedelta import relativedelta

start = datetime(2020, 1, 1)
end = datetime(2025, 10, 1)
months = (end.year - start.year) * 12 + (end.month - start.month) + 1
print(f"Months: {months}")  # Output: 70
```

### Calculate Days Needed (Free Tier)

```
Days = ceil(API Calls / 25)
```

Example:
- 70 months = 70 API calls
- 70 / 25 = 2.8 days
- Round up = **3 days**

## 🎛️ Best Practices

### 1. Start Small

Test with a small date range first:
```bash
# Test with 1 month
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2025-09 \
  --end-date 2025-09 \
  --interval 1min
```

### 2. Use Higher Intervals for Long Periods

If you need 10+ years of data, consider using 5min or 15min intervals instead of 1min to reduce storage and processing time.

```bash
# 15 years of 5-minute data
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2010-01 \
  --end-date 2025-10 \
  --interval 5min
```

### 3. Download in Batches

If you need multiple symbols over long periods, download them across multiple days:

**Day 1:**
```bash
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2020-01 \
  --end-date 2021-12 \
  --interval 1min
```

**Day 2:**
```bash
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2022-01 \
  --end-date 2023-12 \
  --interval 1min
```

### 4. Resume Interrupted Downloads

The system is idempotent - you can safely re-run the same command. It will:
- Skip already downloaded data
- Only download missing months
- Update any changed data

```bash
# Safe to run multiple times
python -m data.alphavantage.equities.intraday \
  --symbol SPY \
  --start-date 2020-01 \
  --end-date 2025-10 \
  --interval 1min
```

### 5. Monitor Progress

The script provides detailed progress information:
- Current month being processed
- Progress percentage
- Total bars inserted/updated
- Any errors encountered

## 🔍 Verify Downloaded Data

After downloading, verify your data:

```sql
-- Check data coverage
SELECT * FROM intraday_data_coverage 
WHERE symbol = 'SPY' AND interval = '1min'
ORDER BY first_bar;

-- Count total bars
SELECT 
    symbol,
    interval,
    COUNT(*) as total_bars,
    MIN(time) as first_bar,
    MAX(time) as last_bar
FROM market_data_intraday
WHERE symbol = 'SPY' AND interval = '1min'
GROUP BY symbol, interval;

-- Check for gaps
SELECT 
    DATE(time) as date,
    COUNT(*) as bars_in_day
FROM market_data_intraday
WHERE symbol = 'SPY' AND interval = '1min'
GROUP BY DATE(time)
ORDER BY date;
```

## 🐍 Programmatic Usage

You can also use the functions directly in Python:

```python
from data.alphavantage.equities.intraday import (
    download_symbol_date_range,
    download_multiple_symbols_date_range,
    generate_month_range
)

# Single symbol
inserted, updated, errors = download_symbol_date_range(
    symbol='SPY',
    start_date='2020-01',
    end_date='2020-12',
    interval='1min',
    adjusted=True,
    extended_hours=True
)

print(f"Inserted: {inserted}, Updated: {updated}")
if errors:
    print(f"Errors: {errors}")

# Multiple symbols
stats = download_multiple_symbols_date_range(
    symbols=['SPY', 'QQQ', 'IWM'],
    start_date='2024-01',
    end_date='2024-12',
    interval='5min'
)

print(stats)

# Just generate month list
months = generate_month_range('2020-01', '2025-10')
print(f"Months to download: {len(months)}")
print(f"First 5: {months[:5]}")
```

## 🚨 Troubleshooting

### "Exceeds free tier daily limit" Warning

**Cause**: You're trying to download more than 25 months in one run.

**Solutions**:
1. Split the download across multiple days
2. Reduce the date range
3. Use a premium API key

### "Rate limit exceeded" Error

**Cause**: Too many API calls in a short time.

**Solutions**:
- Wait 1 minute and try again
- The script should handle this automatically with 15-sec delays

### "No data returned" for Historical Months

**Cause**: Some months may not have data (company not yet public, market holidays, etc.)

**Solutions**:
- This is normal and expected
- The script will log it and continue to the next month

### Database Connection Errors

**Cause**: TimescaleDB is not running.

**Solutions**:
```bash
# Start the database
docker-compose -f infrastructure/database/docker-compose.yml up -d

# Verify it's running
docker ps | grep timescaledb
```

## 📈 Example Workflow: Building a Complete Database

### Goal: Download 5 years of 1-minute data for top 10 tech stocks

**Symbols**: AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA, NFLX, AMD, INTC

**Period**: 2020-01 to 2024-12 (60 months)

**Total API calls**: 10 symbols × 60 months = **600 API calls**

**Days needed**: 600 / 25 = **24 days**

#### Daily Plan:

```bash
#!/bin/bash
# download_tech_stocks.sh

# Day 1: AAPL (60 months, starts at 2020-01)
python -m data.alphavantage.equities.intraday \
  --symbol AAPL --start-date 2020-01 --end-date 2024-12 --interval 1min

# Wait for next day...

# Day 2: MSFT
python -m data.alphavantage.equities.intraday \
  --symbol MSFT --start-date 2020-01 --end-date 2024-12 --interval 1min

# Continue for other symbols...
```

Or use a more efficient approach with partial years:

```bash
# Days 1-5: All symbols for 2020-2021 (2 years = 24 months each = 240 total)
python -m data.alphavantage.equities.intraday \
  --symbols AAPL MSFT GOOGL AMZN META TSLA NVDA NFLX AMD INTC \
  --start-date 2020-01 --end-date 2021-12 --interval 1min

# Days 6-10: All symbols for 2022-2023
python -m data.alphavantage.equities.intraday \
  --symbols AAPL MSFT GOOGL AMZN META TSLA NVDA NFLX AMD INTC \
  --start-date 2022-01 --end-date 2023-12 --interval 1min

# Days 11-12: All symbols for 2024
python -m data.alphavantage.equities.intraday \
  --symbols AAPL MSFT GOOGL AMZN META TSLA NVDA NFLX AMD INTC \
  --start-date 2024-01 --end-date 2024-12 --interval 1min
```

This completes the download in **12 days** instead of 24!

## 🎓 Summary

The date range download feature makes it easy to build comprehensive historical databases for backtesting. Key takeaways:

1. ✅ **Easy to use**: Interactive mode guides you through
2. ✅ **Automatic**: Handles month-by-month downloads
3. ✅ **Safe**: Respects rate limits and handles errors
4. ✅ **Resumable**: Can restart interrupted downloads
5. ⚠️ **Plan ahead**: Free tier has limits - calculate API calls needed
6. ⚠️ **Be patient**: Large downloads take time but run automatically

Happy downloading! 🚀

