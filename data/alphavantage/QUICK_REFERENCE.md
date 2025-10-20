# Alpha Vantage Intraday - Quick Reference Card

## 🚀 One-Liners

```bash
# Interactive mode (easiest)
python -m data.alphavantage.equities.intraday

# Recent data (last 30 days)
python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min

# Single month
python -m data.alphavantage.equities.intraday --symbol SPY --month 2024-01 --interval 1min

# Date range (NEW!)
python -m data.alphavantage.equities.intraday --symbol SPY --start-date 2024-01 --end-date 2024-12 --interval 1min

# Multiple symbols
python -m data.alphavantage.equities.intraday --symbols SPY QQQ IWM --start-date 2024-01 --end-date 2024-12 --interval 5min
```

## 📊 Available Intervals

- `1min` - 1 minute bars (most granular)
- `5min` - 5 minute bars
- `15min` - 15 minute bars
- `30min` - 30 minute bars
- `60min` - 60 minute bars (1 hour)

## 🎯 Common Use Cases

### Backtest Last Year
```bash
python -m data.alphavantage.equities.intraday \
  --symbol AAPL --start-date 2024-01 --end-date 2024-12 --interval 1min
```
**12 months = 12 API calls = ~3 minutes**

### Build 5-Year Database
```bash
# Day 1-3 (split to stay within free tier)
python -m data.alphavantage.equities.intraday \
  --symbol SPY --start-date 2020-01 --end-date 2021-12 --interval 5min
python -m data.alphavantage.equities.intraday \
  --symbol SPY --start-date 2022-01 --end-date 2023-12 --interval 5min
python -m data.alphavantage.equities.intraday \
  --symbol SPY --start-date 2024-01 --end-date 2024-12 --interval 5min
```

### Portfolio Analysis
```bash
python -m data.alphavantage.equities.intraday \
  --symbols SPY QQQ IWM TLT GLD \
  --start-date 2024-01 --end-date 2024-12 --interval 5min
```
**5 symbols × 12 months = 60 API calls = needs 3 days (free tier)**

## 📋 API Limits Cheat Sheet

### Free Tier
- **25 calls/day** (75 hours of 1min data per day)
- **5 calls/minute** (handled automatically)

### Quick Math
```
API Calls = Symbols × Months

Months = (End Year - Start Year) × 12 + (End Month - Start Month) + 1

Days Needed = ⌈API Calls / 25⌉
```

### Examples
| Range | Symbols | Months | API Calls | Days |
|-------|---------|--------|-----------|------|
| 1 month | 1 | 1 | 1 | 1 |
| 1 year | 1 | 12 | 12 | 1 |
| 5 years | 1 | 60 | 60 | 3 |
| 1 year | 3 | 12 | 36 | 2 |
| 5 years | 10 | 60 | 600 | 24 |

## 🔍 Verify Your Data

```sql
-- Summary
SELECT * FROM intraday_data_coverage;

-- Count bars
SELECT symbol, interval, COUNT(*) as bars
FROM market_data_intraday
WHERE symbol = 'SPY'
GROUP BY symbol, interval;

-- Date range
SELECT symbol, interval, MIN(time), MAX(time)
FROM market_data_intraday
WHERE symbol = 'SPY' AND interval = '1min'
GROUP BY symbol, interval;
```

## 🐍 Python API

```python
from data.alphavantage.equities.intraday import (
    download_symbol_date_range,
    generate_month_range
)

# Single symbol
inserted, updated, errors = download_symbol_date_range(
    symbol='SPY',
    start_date='2024-01',
    end_date='2024-12',
    interval='1min'
)

# Generate months
months = generate_month_range('2020-01', '2025-10')
print(f"Will download {len(months)} months")
```

## ⚡ Pro Tips

1. **Start small**: Test with 1 month first
2. **Use interactive mode**: Easiest way to learn
3. **Higher intervals for long periods**: Use 5min/15min for 5+ years
4. **Safe to re-run**: System skips existing data
5. **Check limits**: Run test script to estimate API calls

## 🧪 Test Before Downloading

```bash
# See API call estimates
python data/alphavantage/test_date_range.py

# Get help
python -m data.alphavantage.equities.intraday --help
```

## 📖 Full Documentation

- **Comprehensive Guide**: `data/alphavantage/docs/DATE_RANGE_GUIDE.md`
- **Module README**: `data/alphavantage/README.md`
- **Implementation Summary**: `DATE_RANGE_IMPLEMENTATION_SUMMARY.md`

## 🆘 Troubleshooting

### Rate Limit Error
**Wait 1 minute** - script has 15-sec delays, this shouldn't happen

### Database Connection Error
```bash
docker-compose -f infrastructure/database/docker-compose.yml up -d
```

### API Key Error
```bash
# Make sure .env.local exists with:
ALPHAVANTAGE_API_KEY=your_key_here
```

### "Exceeds free tier" Warning
**Split the download** across multiple days or use a premium key

## ✅ Quick Checklist

Before large downloads:
- [ ] Database is running (`docker ps`)
- [ ] API key is set (`.env.local`)
- [ ] Calculated API calls needed
- [ ] Within daily limit or have multi-day plan
- [ ] Tested with small range first

---

**Need help?** Read the full guide: `data/alphavantage/docs/DATE_RANGE_GUIDE.md`

