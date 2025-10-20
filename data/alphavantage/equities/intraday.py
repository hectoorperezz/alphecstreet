"""
Download intraday equity data from Alpha Vantage.

Supports: 1min, 5min, 15min, 30min, 60min intervals
Features: Adjusted prices, extended hours, historical months (20+ years)
"""

import sys
import argparse
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd

from data.alphavantage.core.api_client import make_api_request
from data.database import get_db_connection, query_to_dataframe, DatabaseConfig


VALID_INTERVALS = ['1min', '5min', '15min', '30min', '60min']


def fetch_intraday_data(
    symbol: str,
    interval: str = '1min',
    adjusted: bool = True,
    extended_hours: bool = True,
    month: Optional[str] = None,
    outputsize: str = 'full'
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch intraday data from Alpha Vantage API.
    
    Args:
        symbol: Stock symbol (e.g., 'SPY', 'AAPL')
        interval: Time interval ('1min', '5min', '15min', '30min', '60min')
        adjusted: True for split/dividend adjusted data (default: True)
        extended_hours: True to include pre/post market 4am-8pm ET (default: True)
        month: Specific month YYYY-MM (e.g., '2020-01'). Available from 2000-01
        outputsize: 'compact' (100 bars) or 'full' (30 days or full month)
    
    Returns:
        Tuple of (DataFrame, error_message)
        DataFrame columns: time, open, high, low, close, volume
    
    Notes:
        - With 'month' parameter, can access 20+ years of historical data
        - extended_hours=False returns only 9:30am-4:00pm ET
        - adjusted=True adjusts for splits and dividends
    
    Example:
        # Get last 30 days of 1-minute data
        df, err = fetch_intraday_data('SPY', '1min')
        
        # Get specific historical month
        df, err = fetch_intraday_data('SPY', '5min', month='2020-01')
    """
    if interval not in VALID_INTERVALS:
        return None, f"Invalid interval: {interval}. Must be one of {VALID_INTERVALS}"
    
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': interval,
        'adjusted': str(adjusted).lower(),
        'extended_hours': str(extended_hours).lower(),
        'datatype': 'json'
    }
    
    # When using month parameter, ALSO include outputsize=full to get complete month
    if month:
        params['month'] = month
        params['outputsize'] = 'full'  # Required to get full month of data
    else:
        params['outputsize'] = outputsize
    
    msg = f"  📥 Fetching {symbol} {interval}"
    if month:
        msg += f" (month: {month})"
    if not extended_hours:
        msg += " [regular hours only]"
    print(msg + "...")
    
    try:
        data = make_api_request(params)
        
        # Check for API errors
        if 'Error Message' in data:
            error_msg = data['Error Message']
            if month:
                return None, f"API Error for {month}: {error_msg} (Note: Symbol may not have traded in this period)"
            return None, f"API Error: {error_msg}"
        
        if 'Note' in data:
            return None, f"API Rate Limit: {data['Note']}"
        
        # Extract time series data
        time_series_key = f'Time Series ({interval})'
        if time_series_key not in data:
            return None, f"No data returned for {symbol}. Keys: {list(data.keys())}"
        
        time_series = data[time_series_key]
        
        if not time_series:
            if month:
                return None, f"No data for {symbol} in {month} (Symbol may not have traded in this period)"
            return None, f"Empty time series for {symbol}"
        
        # Convert to DataFrame
        records = []
        for timestamp_str, values in time_series.items():
            records.append({
                'time': timestamp_str,
                'open': float(values['1. open']),
                'high': float(values['2. high']),
                'low': float(values['3. low']),
                'close': float(values['4. close']),
                'volume': int(values['5. volume'])
            })
        
        df = pd.DataFrame(records)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')
        
        print(f"  ✅ Fetched {len(df)} bars ({df['time'].min()} to {df['time'].max()})")
        
        return df, None
        
    except Exception as e:
        return None, str(e)


def get_last_intraday_time(
    symbol: str,
    interval: str,
    config: Optional[DatabaseConfig] = None
) -> Optional[pd.Timestamp]:
    """
    Get the last timestamp for a symbol/interval in the database.
    
    Returns:
        Last timestamp or None if no data exists
    """
    result = query_to_dataframe("""
        SELECT MAX("time") as last_time
        FROM market_data_intraday
        WHERE symbol = %s AND interval = %s
    """, (symbol, interval), config)
    
    if result.empty or pd.isna(result['last_time'].iloc[0]):
        return None
    
    return result['last_time'].iloc[0]


def insert_intraday_data(
    df: pd.DataFrame,
    symbol: str,
    interval: str,
    config: Optional[DatabaseConfig] = None
) -> Tuple[int, int]:
    """
    Insert intraday data into database.
    
    Args:
        df: DataFrame with columns: time, open, high, low, close, volume
        symbol: Stock symbol
        interval: Time interval
        config: Database configuration
    
    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if df.empty:
        return 0, 0
    
    inserted = 0
    updated = 0
    
    with get_db_connection(config) as conn:
        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO market_data_intraday 
                        ("time", symbol, interval, open, high, low, close, volume, data_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'alphavantage')
                    ON CONFLICT ("time", symbol, interval)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        updated_at = NOW()
                    RETURNING (xmax = 0) AS inserted
                """, (
                    row['time'],
                    symbol,
                    interval,
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ))
                
                result = cursor.fetchone()
                if result and result[0]:
                    inserted += 1
                else:
                    updated += 1
    
    return inserted, updated


def download_symbol_intraday(
    symbol: str,
    interval: str = '1min',
    adjusted: bool = True,
    extended_hours: bool = True,
    month: Optional[str] = None,
    config: Optional[DatabaseConfig] = None
) -> Tuple[int, int, Optional[str]]:
    """
    Download intraday data for a single symbol.
    
    Args:
        symbol: Stock symbol
        interval: Time interval
        adjusted: Adjusted for splits/dividends
        extended_hours: Include pre/post market
        month: Specific month (YYYY-MM)
        config: Database configuration
    
    Returns:
        Tuple of (inserted_count, updated_count, error_message)
    """
    print(f"\n[{symbol}] Processing {interval} data...")
    
    # Check existing data
    last_time = get_last_intraday_time(symbol, interval, config)
    if last_time and not month:
        print(f"  ℹ️  Last data: {last_time}")
    elif not month:
        print(f"  ℹ️  No existing data for {symbol} {interval}")
    
    # Fetch from API
    df, error = fetch_intraday_data(symbol, interval, adjusted, extended_hours, month)
    
    if error:
        print(f"  ❌ Error: {error}")
        return 0, 0, error
    
    if df is None or df.empty:
        print(f"  ⚠️  No data returned")
        return 0, 0, "No data returned"
    
    # Filter to only new data if we have existing data
    if last_time and not month:
        original_len = len(df)
        df = df[df['time'] > last_time]
        if len(df) < original_len:
            print(f"  📊 Filtered to {len(df)} new bars (had {original_len} total)")
    
    if df.empty:
        print(f"  ✅ Already up to date")
        return 0, 0, None
    
    # Insert into database
    print(f"  💾 Inserting {len(df)} bars into database...")
    inserted, updated = insert_intraday_data(df, symbol, interval, config)
    
    print(f"  ✅ Inserted: {inserted}, Updated: {updated}")
    
    return inserted, updated, None


def generate_month_range(start_date: str, end_date: str) -> List[str]:
    """
    Generate list of months in YYYY-MM format between two dates.
    
    Args:
        start_date: Start date in YYYY-MM or YYYY-MM-DD format
        end_date: End date in YYYY-MM or YYYY-MM-DD format
    
    Returns:
        List of months in YYYY-MM format
    
    Example:
        >>> generate_month_range('2020-01', '2020-03')
        ['2020-01', '2020-02', '2020-03']
    """
    # Parse dates
    if len(start_date) == 7:  # YYYY-MM
        start = datetime.strptime(start_date, '%Y-%m')
    else:  # YYYY-MM-DD
        start = datetime.strptime(start_date[:7], '%Y-%m')
    
    if len(end_date) == 7:  # YYYY-MM
        end = datetime.strptime(end_date, '%Y-%m')
    else:  # YYYY-MM-DD
        end = datetime.strptime(end_date[:7], '%Y-%m')
    
    # Generate month list
    months = []
    current = start
    while current <= end:
        months.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)
    
    return months


def download_symbol_date_range(
    symbol: str,
    start_date: str,
    end_date: str,
    interval: str = '1min',
    adjusted: bool = True,
    extended_hours: bool = True,
    config: Optional[DatabaseConfig] = None
) -> Tuple[int, int, List[str]]:
    """
    Download intraday data for a date range by fetching each month sequentially.
    
    Args:
        symbol: Stock symbol
        start_date: Start date (YYYY-MM or YYYY-MM-DD)
        end_date: End date (YYYY-MM or YYYY-MM-DD)
        interval: Time interval
        adjusted: Adjusted for splits/dividends
        extended_hours: Include pre/post market
        config: Database configuration
    
    Returns:
        Tuple of (total_inserted, total_updated, list_of_errors)
    
    Example:
        >>> download_symbol_date_range('SPY', '2020-01', '2020-12', '1min')
        Downloads all months from Jan 2020 to Dec 2020
    """
    print(f"\n{'='*70}")
    print(f"📅 DATE RANGE DOWNLOAD: {symbol}")
    print(f"{'='*70}")
    print(f"Symbol: {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Interval: {interval}")
    print(f"{'='*70}\n")
    
    # Generate month list
    months = generate_month_range(start_date, end_date)
    total_months = len(months)
    
    print(f"📊 Will download {total_months} months: {months[0]} to {months[-1]}")
    print(f"⏱️  Estimated time: ~{total_months * 15} seconds (with rate limiting)\n")
    
    total_inserted = 0
    total_updated = 0
    errors = []
    skipped_months = []  # Months with no data (stock not trading yet)
    
    for i, month in enumerate(months, 1):
        print(f"\n{'─'*70}")
        print(f"[{i}/{total_months}] Processing {month}")
        print(f"{'─'*70}")
        
        inserted, updated, error = download_symbol_intraday(
            symbol=symbol,
            interval=interval,
            adjusted=adjusted,
            extended_hours=extended_hours,
            month=month,
            config=config
        )
        
        total_inserted += inserted
        total_updated += updated
        
        if error:
            # Distinguish between "no data for period" vs actual errors
            if "may not have traded" in error or "No data" in error:
                skipped_months.append(month)
                print(f"  ℹ️  Skipped: {error}")
            else:
                errors.append(f"{month}: {error}")
        
        # Progress update
        pct_complete = (i / total_months) * 100
        print(f"\n📊 Progress: {i}/{total_months} ({pct_complete:.1f}%)")
        print(f"   Total so far - Inserted: {total_inserted:,}, Updated: {total_updated:,}")
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"✅ DATE RANGE DOWNLOAD COMPLETE")
    print(f"{'='*70}")
    print(f"Symbol: {symbol}")
    print(f"Period: {start_date} to {end_date} ({total_months} months)")
    print(f"Total inserted: {total_inserted:,} bars")
    print(f"Total updated: {total_updated:,} bars")
    
    if skipped_months:
        print(f"ℹ️  Skipped months (no data): {len(skipped_months)}")
        if len(skipped_months) <= 5:
            print(f"   Months: {', '.join(skipped_months)}")
        else:
            print(f"   First skipped: {skipped_months[0]}, Last skipped: {skipped_months[-1]}")
    
    if errors:
        print(f"❌ Errors: {len(errors)}")
        for err in errors:
            print(f"   - {err}")
    else:
        print(f"✅ No errors")
    print(f"{'='*70}\n")
    
    return total_inserted, total_updated, errors


def download_multiple_symbols_date_range(
    symbols: List[str],
    start_date: str,
    end_date: str,
    interval: str = '1min',
    adjusted: bool = True,
    extended_hours: bool = True,
    config: Optional[DatabaseConfig] = None
) -> dict:
    """
    Download intraday data for multiple symbols over a date range.
    
    Args:
        symbols: List of stock symbols
        start_date: Start date (YYYY-MM or YYYY-MM-DD)
        end_date: End date (YYYY-MM or YYYY-MM-DD)
        interval: Time interval
        adjusted: Adjusted for splits/dividends
        extended_hours: Include pre/post market
        config: Database configuration
    
    Returns:
        Statistics dictionary
    """
    print(f"\n{'='*70}")
    print(f"🚀 BULK DATE RANGE DOWNLOAD")
    print(f"{'='*70}")
    print(f"Symbols: {', '.join(symbols)} ({len(symbols)} total)")
    print(f"Period: {start_date} to {end_date}")
    print(f"Interval: {interval}")
    print(f"{'='*70}\n")
    
    months = generate_month_range(start_date, end_date)
    total_api_calls = len(symbols) * len(months)
    estimated_minutes = (total_api_calls * 15) / 60  # 15 sec per call with rate limit
    
    print(f"⚠️  This will make {total_api_calls:,} API calls")
    print(f"⏱️  Estimated time: {estimated_minutes:.1f} minutes")
    print(f"📊 Free tier limit: 25 calls/day, 5 calls/minute")
    
    if total_api_calls > 25:
        print(f"\n⚠️  WARNING: This exceeds the free tier daily limit!")
        print(f"   You may need a premium API key or split across multiple days.\n")
    
    proceed = input("\nProceed? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Cancelled.")
        return {'cancelled': True}
    
    stats = {
        'total_symbols': len(symbols),
        'total_months': len(months),
        'total_api_calls': total_api_calls,
        'success_symbols': 0,
        'failed_symbols': 0,
        'total_inserted': 0,
        'total_updated': 0,
        'all_errors': []
    }
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n\n{'█'*70}")
        print(f"SYMBOL {i}/{len(symbols)}: {symbol}")
        print(f"{'█'*70}")
        
        inserted, updated, errors = download_symbol_date_range(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            adjusted=adjusted,
            extended_hours=extended_hours,
            config=config
        )
        
        stats['total_inserted'] += inserted
        stats['total_updated'] += updated
        
        if errors:
            stats['failed_symbols'] += 1
            stats['all_errors'].extend([f"{symbol}: {e}" for e in errors])
        else:
            stats['success_symbols'] += 1
    
    # Final summary
    print(f"\n\n{'='*70}")
    print(f"🎉 BULK DOWNLOAD COMPLETE")
    print(f"{'='*70}")
    print(f"Symbols processed: {len(symbols)}")
    print(f"✅ Success: {stats['success_symbols']}")
    print(f"❌ Failed: {stats['failed_symbols']}")
    print(f"📊 Total inserted: {stats['total_inserted']:,} bars")
    print(f"📊 Total updated: {stats['total_updated']:,} bars")
    if stats['all_errors']:
        print(f"\n❌ Errors ({len(stats['all_errors'])}):")
        for err in stats['all_errors'][:10]:  # Show first 10
            print(f"   - {err}")
        if len(stats['all_errors']) > 10:
            print(f"   ... and {len(stats['all_errors']) - 10} more")
    print(f"{'='*70}\n")
    
    return stats


def download_multiple_symbols(
    symbols: List[str],
    interval: str = '1min',
    adjusted: bool = True,
    extended_hours: bool = True,
    month: Optional[str] = None,
    config: Optional[DatabaseConfig] = None
) -> dict:
    """
    Download intraday data for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        interval: Time interval
        adjusted: Adjusted for splits/dividends
        extended_hours: Include pre/post market
        month: Specific month (YYYY-MM)
        config: Database configuration
    
    Returns:
        Statistics dictionary
    """
    print(f"\n{'='*70}")
    print(f"📊 ALPHA VANTAGE - EQUITIES INTRADAY DATA")
    print(f"{'='*70}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Interval: {interval}")
    print(f"Adjusted: {adjusted}")
    print(f"Extended Hours: {extended_hours}")
    if month:
        print(f"Month: {month}")
    print(f"{'='*70}\n")
    
    stats = {
        'total': len(symbols),
        'success': 0,
        'failed': 0,
        'up_to_date': 0,
        'total_inserted': 0,
        'total_updated': 0
    }
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}")
        
        inserted, updated, error = download_symbol_intraday(
            symbol, interval, adjusted, extended_hours, month, config
        )
        
        if error:
            stats['failed'] += 1
        elif inserted == 0 and updated == 0:
            stats['up_to_date'] += 1
        else:
            stats['success'] += 1
            stats['total_inserted'] += inserted
            stats['total_updated'] += updated
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 DOWNLOAD COMPLETE")
    print(f"{'='*70}")
    print(f"Total symbols: {stats['total']}")
    print(f"✅ Success: {stats['success']}")
    print(f"⏭️  Up to date: {stats['up_to_date']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"📊 Total inserted: {stats['total_inserted']:,} bars")
    print(f"📊 Total updated: {stats['total_updated']:,} bars")
    print(f"{'='*70}\n")
    
    return stats


def download_interactive():
    """Interactive mode - prompts user for inputs."""
    print("\n" + "="*70)
    print("📊 ALPHA VANTAGE - EQUITIES INTRADAY DATA")
    print("="*70 + "\n")
    
    print("This downloads intraday OHLCV data for stocks.")
    print("Press Ctrl+C at any time to cancel.\n")
    
    # Get symbol(s) with retry loop
    while True:
        symbol_input = input("Enter stock symbol(s) (comma-separated, e.g., SPY, AAPL, MSFT): ").strip()
        if symbol_input:
            break
        print("⚠️  Please enter at least one symbol, or press Ctrl+C to cancel.\n")
    
    symbols = [s.strip().upper() for s in symbol_input.replace(',', ' ').split()]
    
    # Get interval with validation
    print(f"\nAvailable intervals: {', '.join(VALID_INTERVALS)}")
    while True:
        interval = input("Enter interval [default: 1min]: ").strip() or '1min'
        if interval in VALID_INTERVALS:
            break
        print(f"⚠️  Invalid interval '{interval}'. Please choose from: {', '.join(VALID_INTERVALS)}\n")
    
    # Get adjusted
    while True:
        adjusted_input = input("\nAdjusted for splits/dividends? (y/n) [default: y]: ").strip().lower() or 'y'
        if adjusted_input in ['y', 'n']:
            adjusted = adjusted_input == 'y'
            break
        print("⚠️  Please enter 'y' or 'n'\n")
    
    # Get extended hours
    while True:
        extended_input = input("Include pre/post market hours? (y/n) [default: y]: ").strip().lower() or 'y'
        if extended_input in ['y', 'n']:
            extended_hours = extended_input == 'y'
            break
        print("⚠️  Please enter 'y' or 'n'\n")
    
    # Choose download mode
    print("\n" + "─"*70)
    print("📅 DOWNLOAD MODE")
    print("─"*70)
    print("1. Recent data (last 30 days)")
    print("2. Single month (YYYY-MM)")
    print("3. Date range (downloads multiple months in batches)")
    print("─"*70)
    
    while True:
        mode = input("Choose mode (1/2/3) [default: 1]: ").strip() or '1'
        if mode in ['1', '2', '3']:
            break
        print("⚠️  Please enter 1, 2, or 3\n")
    
    if mode == '1':
        # Recent data (default)
        print()
        stats = download_multiple_symbols(symbols, interval, adjusted, extended_hours, None)
        
        if stats.get('failed', 0) > 0:
            sys.exit(1)
    
    elif mode == '2':
        # Single month
        print("\nEnter month in YYYY-MM format (available from 2000-01)")
        while True:
            month = input("Month (e.g., 2020-01): ").strip()
            if month and len(month) == 7 and month[4] == '-':
                try:
                    datetime.strptime(month, '%Y-%m')
                    break
                except ValueError:
                    print("⚠️  Invalid format. Use YYYY-MM (e.g., 2020-01)\n")
            else:
                print("⚠️  Invalid format. Use YYYY-MM (e.g., 2020-01)\n")
        
        print()
        stats = download_multiple_symbols(symbols, interval, adjusted, extended_hours, month)
        
        if stats.get('failed', 0) > 0:
            sys.exit(1)
    
    else:  # mode == '3'
        # Date range
        print("\n" + "─"*70)
        print("📅 DATE RANGE DOWNLOAD")
        print("─"*70)
        print("This will download data month-by-month for the entire range.")
        print("Each month requires 1 API call (15 sec delay between calls).")
        print("─"*70 + "\n")
        
        # Get start date
        while True:
            start_date = input("Start date (YYYY-MM, e.g., 2020-01): ").strip()
            if start_date and len(start_date) == 7 and start_date[4] == '-':
                try:
                    datetime.strptime(start_date, '%Y-%m')
                    break
                except ValueError:
                    print("⚠️  Invalid format. Use YYYY-MM (e.g., 2020-01)\n")
            else:
                print("⚠️  Invalid format. Use YYYY-MM (e.g., 2020-01)\n")
        
        # Get end date
        while True:
            end_date = input("End date (YYYY-MM, e.g., 2025-10): ").strip()
            if end_date and len(end_date) == 7 and end_date[4] == '-':
                try:
                    end_dt = datetime.strptime(end_date, '%Y-%m')
                    start_dt = datetime.strptime(start_date, '%Y-%m')
                    if end_dt >= start_dt:
                        break
                    else:
                        print("⚠️  End date must be >= start date\n")
                except ValueError:
                    print("⚠️  Invalid format. Use YYYY-MM (e.g., 2025-10)\n")
            else:
                print("⚠️  Invalid format. Use YYYY-MM (e.g., 2025-10)\n")
        
        # Download for multiple symbols or single
        if len(symbols) == 1:
            print()
            total_inserted, total_updated, errors = download_symbol_date_range(
                symbols[0], start_date, end_date, interval, adjusted, extended_hours
            )
            if errors:
                sys.exit(1)
        else:
            print()
            stats = download_multiple_symbols_date_range(
                symbols, start_date, end_date, interval, adjusted, extended_hours
            )
            if stats.get('cancelled') or stats.get('failed_symbols', 0) > 0:
                sys.exit(1)


def main():
    """Main entry point with CLI and interactive modes."""
    parser = argparse.ArgumentParser(
        description='Download intraday equity data from Alpha Vantage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python -m data.alphavantage.equities.intraday
  
  # Command line mode - recent data
  python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min
  
  # Multiple symbols
  python -m data.alphavantage.equities.intraday --symbols SPY QQQ IWM --interval 5min
  
  # Historical month (20+ years available)
  python -m data.alphavantage.equities.intraday --symbol AAPL --interval 1min --month 2020-01
  
  # Date range (downloads month-by-month)
  python -m data.alphavantage.equities.intraday --symbol SPY --start-date 2020-01 --end-date 2020-12 --interval 1min
  
  # Multiple symbols for a date range
  python -m data.alphavantage.equities.intraday --symbols SPY QQQ --start-date 2024-01 --end-date 2024-12 --interval 5min
  
  # Regular hours only
  python -m data.alphavantage.equities.intraday --symbol SPY --no-extended-hours
        """
    )
    
    parser.add_argument('--symbol', help='Single symbol to download')
    parser.add_argument('--symbols', nargs='+', help='Multiple symbols')
    parser.add_argument('--interval', choices=VALID_INTERVALS, default='1min')
    parser.add_argument('--month', help='Historical month (YYYY-MM, from 2000-01)')
    parser.add_argument('--start-date', help='Start date for range download (YYYY-MM)')
    parser.add_argument('--end-date', help='End date for range download (YYYY-MM)')
    parser.add_argument('--no-adjusted', action='store_true', help='Raw prices (not adjusted)')
    parser.add_argument('--no-extended-hours', action='store_true', help='Regular hours only')
    
    args = parser.parse_args()
    
    # If no arguments, use interactive mode
    if not args.symbol and not args.symbols:
        download_interactive()
        return
    
    # Validate arguments
    if args.month and (args.start_date or args.end_date):
        print("❌ Error: Cannot use --month with --start-date/--end-date")
        sys.exit(1)
    
    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        print("❌ Error: Both --start-date and --end-date are required for range download")
        sys.exit(1)
    
    # CLI mode
    symbols = [args.symbol] if args.symbol else args.symbols
    
    try:
        # Date range mode
        if args.start_date and args.end_date:
            if len(symbols) == 1:
                total_inserted, total_updated, errors = download_symbol_date_range(
                    symbol=symbols[0],
                    start_date=args.start_date,
                    end_date=args.end_date,
                    interval=args.interval,
                    adjusted=not args.no_adjusted,
                    extended_hours=not args.no_extended_hours
                )
                if errors:
                    sys.exit(1)
            else:
                stats = download_multiple_symbols_date_range(
                    symbols=symbols,
                    start_date=args.start_date,
                    end_date=args.end_date,
                    interval=args.interval,
                    adjusted=not args.no_adjusted,
                    extended_hours=not args.no_extended_hours
                )
                if stats.get('cancelled') or stats.get('failed_symbols', 0) > 0:
                    sys.exit(1)
        
        # Single month or recent data mode
        else:
            stats = download_multiple_symbols(
                symbols=symbols,
                interval=args.interval,
                adjusted=not args.no_adjusted,
                extended_hours=not args.no_extended_hours,
                month=args.month
            )
            
            if stats.get('failed', 0) > 0:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

