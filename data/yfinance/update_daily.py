"""
Daily update script for market data.

This script downloads the latest day of data for all S&P 500 stocks.
Designed to run daily via cron or scheduler.
"""

import sys
from datetime import datetime, timedelta
from typing import Optional

from data.database import DatabaseConfig, query_to_dataframe
from data.yfinance.download_sp500_yfinance import download_symbol_data


def get_last_market_date(config: Optional[DatabaseConfig] = None) -> Optional[str]:
    """
    Get the last date we have data for.
    
    Args:
        config: Database configuration (optional)
    
    Returns:
        Last date as string (YYYY-MM-DD) or None if no data
    """
    df = query_to_dataframe(
        'SELECT MAX("time") as last_date FROM market_data_daily',
        config=config
    )
    
    last_date = df["last_date"].iloc[0]
    
    if last_date is None:
        return None
    
    return last_date.strftime("%Y-%m-%d")


def update_daily_data(
    days_back: int = 5,
    config: Optional[DatabaseConfig] = None,
) -> dict[str, int]:
    """
    Update market data with latest data.
    
    Downloads data from N days back to ensure we catch any missed days
    (weekends, holidays, etc.).
    
    Args:
        days_back: Number of days to look back (default: 5)
        config: Database configuration (optional)
    
    Returns:
        Dictionary with update statistics
    
    Example:
        >>> stats = update_daily_data()
        >>> print(f"Updated {stats['success']} symbols")
    """
    # Calculate start date (N days back to catch weekends/holidays)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}")
    print(f"📊 Daily Market Data Update")
    print(f"{'='*60}")
    print(f"Date Range: {start_str} to {end_str}")
    print(f"{'='*60}\n")
    
    # Get last date in database
    last_date = get_last_market_date(config)
    if last_date:
        print(f"📅 Last data in database: {last_date}")
    else:
        print(f"📅 No data in database yet")
    
    # Get active symbols
    symbols_df = query_to_dataframe(
        "SELECT symbol FROM sp500_constituents WHERE is_active = TRUE ORDER BY symbol",
        config=config
    )
    symbols = symbols_df["symbol"].tolist()
    
    print(f"📋 Updating {len(symbols)} symbols...\n")
    
    stats = {
        "total": len(symbols),
        "success": 0,
        "failed": 0,
        "total_bars": 0,
    }
    
    failed_symbols = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}...", end=" ", flush=True)
        
        bars, error = download_symbol_data(symbol, start_str, end_str, config=config)
        
        if error:
            stats["failed"] += 1
            failed_symbols.append((symbol, error))
            print(f"❌ {error}")
        else:
            stats["success"] += 1
            stats["total_bars"] += bars
            print(f"✅ {bars} bars")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 Update Complete")
    print(f"{'='*60}")
    print(f"Total symbols: {stats['total']}")
    print(f"✅ Success: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"📊 Total bars: {stats['total_bars']:,}")
    
    if failed_symbols:
        print(f"\n⚠️  Failed symbols:")
        for symbol, error in failed_symbols[:10]:  # Show first 10
            print(f"   {symbol}: {error}")
        if len(failed_symbols) > 10:
            print(f"   ... and {len(failed_symbols) - 10} more")
    
    print(f"{'='*60}\n")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily market data update")
    parser.add_argument(
        "--days-back",
        type=int,
        default=5,
        help="Number of days to look back (default: 5)"
    )
    
    args = parser.parse_args()
    
    try:
        stats = update_daily_data(days_back=args.days_back)
        
        if stats["failed"] > 0:
            print(f"⚠️  Completed with {stats['failed']} failures")
            sys.exit(1)
        else:
            print("✅ All updates successful!")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
