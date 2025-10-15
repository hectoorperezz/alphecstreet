"""
Download intraday equity data from Alpha Vantage.

Supports: 1min, 5min, 15min, 30min, 60min intervals
Features: Adjusted prices, extended hours, historical months (20+ years)
"""

import sys
import argparse
from typing import Optional, List, Tuple
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
        'outputsize': outputsize,
        'datatype': 'json'
    }
    
    if month:
        params['month'] = month
    
    msg = f"  📥 Fetching {symbol} {interval}"
    if month:
        msg += f" (month: {month})"
    if not extended_hours:
        msg += " [regular hours only]"
    print(msg + "...")
    
    try:
        data = make_api_request(params)
        
        # Extract time series data
        time_series_key = f'Time Series ({interval})'
        if time_series_key not in data:
            return None, f"No data returned for {symbol}. Keys: {list(data.keys())}"
        
        time_series = data[time_series_key]
        
        if not time_series:
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
    print()
    
    # Get symbol(s)
    symbol_input = input("Enter stock symbol(s) (comma-separated, e.g., SPY, AAPL, MSFT): ").strip()
    if not symbol_input:
        print("❌ Symbol is required")
        sys.exit(1)
    
    symbols = [s.strip().upper() for s in symbol_input.replace(',', ' ').split()]
    
    # Get interval
    print(f"\nAvailable intervals: {', '.join(VALID_INTERVALS)}")
    interval = input("Enter interval [default: 1min]: ").strip() or '1min'
    if interval not in VALID_INTERVALS:
        print(f"❌ Invalid interval. Must be one of: {VALID_INTERVALS}")
        sys.exit(1)
    
    # Get adjusted
    adjusted_input = input("\nAdjusted for splits/dividends? (y/n) [default: y]: ").strip().lower() or 'y'
    adjusted = adjusted_input == 'y'
    
    # Get extended hours
    extended_input = input("Include pre/post market hours? (y/n) [default: y]: ").strip().lower() or 'y'
    extended_hours = extended_input == 'y'
    
    # Get month (optional)
    print("\nHistorical month (optional):")
    print("  Leave blank for recent data (last 30 days)")
    print("  Or enter YYYY-MM for specific month (available from 2000-01)")
    month = input("Month [optional]: ").strip() or None
    
    # Download
    print()
    stats = download_multiple_symbols(symbols, interval, adjusted, extended_hours, month)
    
    if stats['failed'] > 0:
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
  
  # Command line mode
  python -m data.alphavantage.equities.intraday --symbol SPY --interval 1min
  
  # Multiple symbols
  python -m data.alphavantage.equities.intraday --symbols SPY QQQ IWM --interval 5min
  
  # Historical month (20+ years available)
  python -m data.alphavantage.equities.intraday --symbol AAPL --interval 1min --month 2020-01
  
  # Regular hours only
  python -m data.alphavantage.equities.intraday --symbol SPY --no-extended-hours
        """
    )
    
    parser.add_argument('--symbol', help='Single symbol to download')
    parser.add_argument('--symbols', nargs='+', help='Multiple symbols')
    parser.add_argument('--interval', choices=VALID_INTERVALS, default='1min')
    parser.add_argument('--month', help='Historical month (YYYY-MM, from 2000-01)')
    parser.add_argument('--no-adjusted', action='store_true', help='Raw prices (not adjusted)')
    parser.add_argument('--no-extended-hours', action='store_true', help='Regular hours only')
    
    args = parser.parse_args()
    
    # If no arguments, use interactive mode
    if not args.symbol and not args.symbols:
        download_interactive()
        return
    
    # CLI mode
    symbols = [args.symbol] if args.symbol else args.symbols
    
    try:
        stats = download_multiple_symbols(
            symbols=symbols,
            interval=args.interval,
            adjusted=not args.no_adjusted,
            extended_hours=not args.no_extended_hours,
            month=args.month
        )
        
        if stats['failed'] > 0:
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

