"""
Add custom tickers to the database.

This script allows you to download historical data for any ticker(s) from yfinance
and store it in the market_data_daily table. It automatically:
- Checks if ticker already exists in database
- Only downloads new data (incremental updates)
- Handles rate limits with retry logic
- Supports both interactive and command-line usage

Usage:
    # Interactive mode
    python -m data.add_tickers
    
    # Command line with single ticker
    python -m data.add_tickers --tickers AAPL
    
    # Command line with multiple tickers
    python -m data.add_tickers --tickers AAPL MSFT GOOGL TSLA
    
    # Specify date range
    python -m data.add_tickers --tickers AAPL --start-date 2020-01-01 --end-date 2025-01-01
    
    # Force re-download even if exists
    python -m data.add_tickers --tickers AAPL --force
"""

import sys
import argparse
from typing import Optional, List
from datetime import datetime

from data.database import query_to_dataframe, DatabaseConfig
from data.yfinance.download_sp500_yfinance import download_symbol_data


def check_ticker_exists(symbol: str, config: Optional[DatabaseConfig] = None) -> bool:
    """
    Check if a ticker already has data in the database.
    
    Args:
        symbol: Ticker symbol to check
        config: Database configuration (optional)
    
    Returns:
        True if ticker has data, False otherwise
    """
    result = query_to_dataframe(
        "SELECT COUNT(*) as count FROM market_data_daily WHERE symbol = %s",
        (symbol,),
        config
    )
    return result['count'].iloc[0] > 0


def get_ticker_info(symbol: str, config: Optional[DatabaseConfig] = None) -> dict:
    """
    Get information about existing ticker data.
    
    Args:
        symbol: Ticker symbol
        config: Database configuration (optional)
    
    Returns:
        Dictionary with ticker info (first_date, last_date, total_rows)
    """
    result = query_to_dataframe("""
        SELECT 
            MIN(time) as first_date,
            MAX(time) as last_date,
            COUNT(*) as total_rows
        FROM market_data_daily
        WHERE symbol = %s
    """, (symbol,), config)
    
    if result.empty or result['total_rows'].iloc[0] == 0:
        return None
    
    return {
        'first_date': result['first_date'].iloc[0],
        'last_date': result['last_date'].iloc[0],
        'total_rows': int(result['total_rows'].iloc[0])
    }


def add_tickers(
    tickers: List[str],
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    force: bool = False,
    config: Optional[DatabaseConfig] = None,
) -> dict:
    """
    Add multiple tickers to the database.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date for historical data (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to today
        force: If True, download even if ticker exists
        config: Database configuration
    
    Returns:
        Statistics dictionary
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n{'='*70}")
    print(f"📊 ADD CUSTOM TICKERS TO DATABASE")
    print(f"{'='*70}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Force download: {force}")
    print(f"{'='*70}\n")
    
    stats = {
        'total': len(tickers),
        'new': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0,
        'total_bars': 0,
    }
    
    for i, symbol in enumerate(tickers, 1):
        symbol = symbol.upper().strip()
        
        print(f"[{i}/{len(tickers)}] Processing {symbol}...")
        
        # Check if ticker exists
        if not force and check_ticker_exists(symbol, config):
            info = get_ticker_info(symbol, config)
            print(f"  ℹ️  {symbol} already in database:")
            print(f"     - Date range: {info['first_date']} to {info['last_date']}")
            print(f"     - Total rows: {info['total_rows']:,}")
            
            # Ask user what to do
            response = input(f"     Update with new data? (y/n/all): ").lower()
            
            if response == 'all':
                # Update this one and all remaining without asking
                force = True
            elif response != 'y':
                print(f"  ⏭️  Skipped {symbol}")
                stats['skipped'] += 1
                print()
                continue
            
            is_update = True
        else:
            is_update = False
        
        # Download data (uses incremental logic internally)
        print(f"  📥 Downloading {symbol}...")
        bars, error = download_symbol_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            config=config,
            skip_existing=True  # Always use incremental
        )
        
        if error:
            stats['failed'] += 1
            print(f"  ❌ Failed: {error}\n")
        elif bars == 0:
            if is_update:
                print(f"  ✅ Already up to date\n")
                stats['updated'] += 1
            else:
                print(f"  ⚠️  No data found for {symbol}\n")
                stats['failed'] += 1
        else:
            if is_update:
                stats['updated'] += 1
                print(f"  ✅ Updated: {bars} new bars\n")
            else:
                stats['new'] += 1
                print(f"  ✅ Added: {bars} bars\n")
            stats['total_bars'] += bars
    
    # Summary
    print(f"{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"Total tickers processed: {stats['total']}")
    print(f"✅ New tickers added: {stats['new']}")
    print(f"🔄 Existing tickers updated: {stats['updated']}")
    print(f"⏭️  Skipped: {stats['skipped']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"📊 Total bars downloaded: {stats['total_bars']:,}")
    print(f"{'='*70}\n")
    
    return stats


def interactive_mode(config: Optional[DatabaseConfig] = None):
    """Interactive mode for adding tickers."""
    print("\n" + "="*70)
    print("📊 INTERACTIVE TICKER DOWNLOADER")
    print("="*70)
    print("Add any ticker(s) to your database. Enter one or more symbols.")
    print("Examples: AAPL, MSFT GOOGL TSLA, BRK.B")
    print("Press Ctrl+C at any time to cancel.")
    print("="*70 + "\n")
    
    # Get tickers with retry loop
    while True:
        ticker_input = input("Enter ticker symbol(s) (space-separated): ").strip()
        if ticker_input:
            break
        print("⚠️  Please enter at least one ticker, or press Ctrl+C to cancel.\n")
    
    tickers = [t.upper().strip() for t in ticker_input.replace(',', ' ').split()]
    
    # Get date range with validation
    while True:
        start_date = input("\nStart date (YYYY-MM-DD) [default: 2015-01-01]: ").strip()
        if not start_date:
            start_date = "2015-01-01"
            break
        
        # Validate format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            break
        except ValueError:
            print("⚠️  Invalid date format. Please use YYYY-MM-DD or leave blank for default.\n")
    
    while True:
        end_date = input("End date (YYYY-MM-DD) [default: today]: ").strip()
        if not end_date:
            end_date = None
            break
        
        # Validate format
        try:
            datetime.strptime(end_date, '%Y-%m-%d')
            break
        except ValueError:
            print("⚠️  Invalid date format. Please use YYYY-MM-DD or leave blank for today.\n")
    
    # Download
    print()
    add_tickers(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        force=False,
        config=config
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add custom tickers to the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python -m data.add_tickers
  
  # Add single ticker
  python -m data.add_tickers --tickers AAPL
  
  # Add multiple tickers
  python -m data.add_tickers --tickers AAPL MSFT GOOGL TSLA
  
  # Specify date range
  python -m data.add_tickers --tickers AAPL --start-date 2020-01-01
  
  # Force re-download (ignore existing data)
  python -m data.add_tickers --tickers AAPL --force
        """
    )
    
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Ticker symbol(s) to download (space-separated)'
    )
    parser.add_argument(
        '--start-date',
        default='2015-01-01',
        help='Start date (YYYY-MM-DD) [default: 2015-01-01]'
    )
    parser.add_argument(
        '--end-date',
        default=None,
        help='End date (YYYY-MM-DD) [default: today]'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force download even if ticker exists'
    )
    
    args = parser.parse_args()
    
    try:
        if args.tickers:
            # Command-line mode
            stats = add_tickers(
                tickers=args.tickers,
                start_date=args.start_date,
                end_date=args.end_date,
                force=args.force
            )
            
            # Exit with error code if any failed
            if stats['failed'] > 0:
                sys.exit(1)
        else:
            # Interactive mode
            interactive_mode()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

