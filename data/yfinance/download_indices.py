"""
Download benchmark indices data from yfinance.

Indices are stored in the same market_data_daily table as stocks,
but tracked separately in benchmark_indices table.
"""

import sys
from typing import Optional

from data.database import (
    execute_command,
    query_to_dataframe,
    DatabaseConfig,
)
from data.yfinance.download_sp500_yfinance import download_symbol_data


def get_active_indices(config: Optional[DatabaseConfig] = None) -> list[tuple[str, str]]:
    """
    Get list of active benchmark indices.
    
    Returns:
        List of tuples: (symbol, name)
    
    Example:
        >>> indices = get_active_indices()
        >>> print(f"Found {len(indices)} indices")
    """
    df = query_to_dataframe(
        "SELECT symbol, name FROM benchmark_indices WHERE is_active = TRUE ORDER BY category, symbol",
        config=config
    )
    return list(zip(df["symbol"].tolist(), df["name"].tolist()))


def download_index_data(
    symbol: str,
    start_date: str,
    end_date: Optional[str] = None,
    config: Optional[DatabaseConfig] = None,
) -> tuple[int, Optional[str]]:
    """
    Download data for a single index/ETF.
    
    Uses the same download_symbol_data function since indices
    have the same OHLCV structure as stocks.
    
    Args:
        symbol: Index symbol (e.g., 'SPY', '^GSPC')
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD (optional)
        config: Database config
    
    Returns:
        Tuple of (bars downloaded, error message if any)
    
    Example:
        >>> bars, error = download_index_data('SPY', '2020-01-01')
        >>> if not error:
        ...     print(f"Downloaded {bars} bars")
    """
    # Download using the same function as stocks (with incremental download)
    bars, error = download_symbol_data(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        config=config,
        skip_existing=True  # Incremental download
    )
    
    # Update benchmark_indices table status
    if not error and bars >= 0:
        execute_command(
            """
            UPDATE benchmark_indices 
            SET last_downloaded = NOW(), 
                download_status = CASE WHEN %s > 0 THEN 'success' ELSE 'up_to_date' END
            WHERE symbol = %s
            """,
            (bars, symbol),
            config
        )
    elif error:
        execute_command(
            """
            UPDATE benchmark_indices 
            SET download_status = 'error'
            WHERE symbol = %s
            """,
            (symbol,),
            config
        )
    
    return bars, error


def download_all_indices(
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    config: Optional[DatabaseConfig] = None,
) -> dict[str, int]:
    """
    Download data for all active benchmark indices.
    
    Args:
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD (optional)
        config: Database config
    
    Returns:
        Statistics dictionary
    
    Example:
        >>> stats = download_all_indices(start_date="2020-01-01")
        >>> print(f"Success: {stats['success']}, Failed: {stats['failed']}")
    """
    print(f"\n{'='*60}")
    print(f"📊 Benchmark Indices Download")
    print(f"{'='*60}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date or 'today'}")
    print(f"{'='*60}\n")
    
    indices = get_active_indices(config)
    
    print(f"📋 Found {len(indices)} active indices\n")
    
    stats = {
        "total": len(indices),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "total_bars": 0,
    }
    
    for i, (symbol, name) in enumerate(indices, 1):
        print(f"[{i}/{len(indices)}] {symbol} ({name})...", end=" ", flush=True)
        
        bars, error = download_index_data(symbol, start_date, end_date, config)
        
        if error:
            stats["failed"] += 1
            print(f"❌ {error}")
        elif bars == 0:
            stats["skipped"] += 1
            print(f"⏭️  Up to date")
        else:
            stats["success"] += 1
            stats["total_bars"] += bars
            print(f"✅ {bars} bars")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Download Complete")
    print(f"{'='*60}")
    print(f"Total indices: {stats['total']}")
    print(f"✅ Success: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⏭️  Skipped: {stats['skipped']}")
    print(f"📊 Total bars: {stats['total_bars']:,}")
    print(f"{'='*60}\n")
    
    return stats


def update_indices_daily(config: Optional[DatabaseConfig] = None) -> dict[str, int]:
    """
    Daily update for benchmark indices.
    
    Uses incremental download, so it's very fast.
    
    Args:
        config: Database config
    
    Returns:
        Statistics dictionary
    
    Example:
        >>> stats = update_indices_daily()
        >>> print(f"Updated {stats['success']} indices")
    """
    from datetime import datetime, timedelta
    
    # Download from 7 days ago to catch any missed days
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    print(f"\n{'='*60}")
    print(f"📊 Daily Benchmark Indices Update")
    print(f"{'='*60}\n")
    
    return download_all_indices(start_date=start_date, config=config)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download benchmark indices")
    parser.add_argument(
        "--start-date",
        default="2015-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="End date (YYYY-MM-DD), defaults to today"
    )
    parser.add_argument(
        "--symbol",
        help="Download single index only"
    )
    parser.add_argument(
        "--daily-update",
        action="store_true",
        help="Daily update (incremental)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.daily_update:
            stats = update_indices_daily()
        elif args.symbol:
            print(f"Downloading {args.symbol}...")
            bars, error = download_index_data(args.symbol, args.start_date, args.end_date)
            if error:
                print(f"❌ Error: {error}")
                sys.exit(1)
            else:
                print(f"✅ Downloaded {bars} bars for {args.symbol}")
        else:
            stats = download_all_indices(
                start_date=args.start_date,
                end_date=args.end_date
            )
            
            if stats["failed"] > 0:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

