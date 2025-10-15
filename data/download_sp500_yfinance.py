"""
Download S&P 500 constituents and historical daily data from yfinance.
"""

import sys
import time
from datetime import datetime, timedelta
from typing import Optional
import uuid
import random

import pandas as pd
import yfinance as yf
from tqdm import tqdm

from data.database import (
    get_db_connection,
    insert_dataframe,
    execute_command,
    query_to_dataframe,
    DatabaseConfig,
)


def fetch_sp500_constituents() -> pd.DataFrame:
    """
    Fetch current S&P 500 constituents from Wikipedia.
    
    Returns:
        DataFrame with columns: symbol, company_name, sector, sub_industry
    
    Example:
        >>> constituents = fetch_sp500_constituents()
        >>> print(f"Downloaded {len(constituents)} S&P 500 stocks")
    """
    print("📥 Downloading S&P 500 constituents from Wikipedia...")
    
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    # Add User-Agent to avoid 403 Forbidden
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req) as response:
        tables = pd.read_html(response)
    
    df = tables[0]
    
    # Rename columns to match our schema
    df = df.rename(columns={
        "Symbol": "symbol",
        "Security": "company_name",
        "GICS Sector": "sector",
        "GICS Sub-Industry": "sub_industry",
        "CIK": "cik",
    })
    
    # Select and clean columns
    df = df[["symbol", "company_name", "sector", "sub_industry", "cik"]]
    
    # Clean symbols (some have dots or special characters)
    df["symbol"] = df["symbol"].str.replace(".", "-", regex=False)
    
    # Convert CIK to string and pad with zeros
    df["cik"] = df["cik"].astype(str).str.zfill(10)
    
    # Add metadata
    df["is_active"] = True
    df["added_at"] = datetime.utcnow()
    df["updated_at"] = datetime.utcnow()
    
    print(f"✅ Downloaded {len(df)} S&P 500 constituents")
    
    return df


def update_sp500_constituents(
    config: Optional[DatabaseConfig] = None
) -> int:
    """
    Download and update S&P 500 constituents in database.
    
    Args:
        config: Database configuration (optional)
    
    Returns:
        Number of constituents inserted/updated
    
    Example:
        >>> count = update_sp500_constituents()
        >>> print(f"Updated {count} constituents")
    """
    df = fetch_sp500_constituents()
    
    with get_db_connection(config) as conn:
        with conn.cursor() as cursor:
            # Upsert each constituent
            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO sp500_constituents 
                        (symbol, company_name, sector, sub_industry, cik, is_active, added_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) 
                    DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        sector = EXCLUDED.sector,
                        sub_industry = EXCLUDED.sub_industry,
                        cik = EXCLUDED.cik,
                        is_active = EXCLUDED.is_active,
                        updated_at = EXCLUDED.updated_at
                """, (
                    row["symbol"],
                    row["company_name"],
                    row["sector"],
                    row["sub_industry"],
                    row["cik"],
                    row["is_active"],
                    row["added_at"],
                    row["updated_at"],
                ))
    
    print(f"💾 Saved {len(df)} constituents to database")
    
    return len(df)


def download_symbol_data(
    symbol: str,
    start_date: str,
    end_date: Optional[str] = None,
    batch_id: Optional[str] = None,
    config: Optional[DatabaseConfig] = None,
    max_retries: int = 3,
    skip_existing: bool = True,
) -> tuple[int, Optional[str]]:
    """
    Download historical daily data for a single symbol from yfinance.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        batch_id: Batch ID for logging (optional)
        config: Database configuration (optional)
        max_retries: Maximum number of retry attempts (default: 3)
        skip_existing: Only download data after last date in DB (default: True)
    
    Returns:
        Tuple of (number of bars downloaded, error message if any)
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    # Check existing data and adjust start_date for incremental download
    original_start_date = start_date
    if skip_existing:
        try:
            existing_data = query_to_dataframe(
                'SELECT MAX("time") as last_date FROM market_data_daily WHERE symbol = %s',
                (symbol,),
                config
            )
            
            if not existing_data.empty and existing_data['last_date'].iloc[0] is not None:
                last_date = existing_data['last_date'].iloc[0]
                
                # Convert to string if needed
                if hasattr(last_date, 'strftime'):
                    last_date_str = last_date.strftime("%Y-%m-%d")
                else:
                    last_date_str = str(last_date)
                
                # If we already have data up to or past the end_date, skip
                if last_date_str >= end_date:
                    # Already up to date
                    return 0, None
                
                # Calculate next day after last_date
                from datetime import datetime as dt
                next_day = dt.strptime(last_date_str, "%Y-%m-%d") + timedelta(days=1)
                next_day_str = next_day.strftime("%Y-%m-%d")
                
                # Adjust start_date to only download new data
                if next_day_str > start_date:
                    start_date = next_day_str
        except Exception as e:
            # If error checking existing data, continue with full download
            pass
    
    download_start = datetime.utcnow()
    
    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            # Add random delay before request (0.5-2 seconds)
            if attempt > 0:
                wait_time = (2 ** attempt) + random.random() * 2  # Exponential backoff
                time.sleep(wait_time)
            
            # Download data from yfinance with session
            import requests
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            })
            
            ticker = yf.Ticker(symbol, session=session)
            
            # Add small random delay
            time.sleep(0.5 + random.random())
            
            df = ticker.history(
                start=start_date, 
                end=end_date, 
                auto_adjust=False,
                timeout=30  # Add timeout
            )
            
            if df.empty:
                error_msg = "No data returned from yfinance"
                _log_download(
                    symbol, original_start_date, end_date, 0, "ERROR", error_msg,
                    download_start, batch_id, config
                )
                return 0, error_msg
            
            # Prepare data for database
            df = df.reset_index()
            df = df.rename(columns={
                "Date": "time",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Adj Close": "adj_close",
            })
            
            # Select only needed columns
            df = df[["time", "open", "high", "low", "close", "volume", "adj_close"]]
            
            # Add symbol
            df["symbol"] = symbol
            
            # Convert date to date only (remove time component)
            df["time"] = pd.to_datetime(df["time"]).dt.date
            
            # Remove any rows with NaN values
            df = df.dropna()
            
            if df.empty:
                error_msg = "All data contained NaN values"
                _log_download(
                    symbol, original_start_date, end_date, 0, "ERROR", error_msg,
                    download_start, batch_id, config
                )
                return 0, error_msg
            
            # Insert into database (with conflict handling)
            with get_db_connection(config) as conn:
                with conn.cursor() as cursor:
                    # Insert data row by row (to handle conflicts)
                    inserted = 0
                    for _, row in df.iterrows():
                        cursor.execute("""
                            INSERT INTO market_data_daily 
                                (time, symbol, open, high, low, close, volume, adj_close)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (time, symbol) 
                            DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume,
                                adj_close = EXCLUDED.adj_close,
                                updated_at = NOW()
                        """, (
                            row["time"],
                            row["symbol"],
                            row["open"],
                            row["high"],
                            row["low"],
                            row["close"],
                            row["volume"],
                            row["adj_close"],
                        ))
                        inserted += 1
            
            # Log success
            _log_download(
                symbol, original_start_date, end_date, inserted, "SUCCESS", None,
                download_start, batch_id, config
            )
            
            # Update constituent download status
            execute_command(
                """
                UPDATE sp500_constituents 
                SET last_downloaded = NOW(), download_status = 'success'
                WHERE symbol = %s
                """,
                (symbol,),
                config
            )
            
            return inserted, None
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower() or "429" in error_msg:
                if attempt < max_retries - 1:
                    # Wait longer and retry
                    wait_time = (2 ** (attempt + 1)) * 5  # Exponential: 10s, 20s, 40s
                    print(f"  ⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Max retries reached
                    error_msg = "Rate limit exceeded after retries"
            
            # Log error
            _log_download(
                symbol, original_start_date, end_date, 0, "ERROR", error_msg,
                download_start, batch_id, config
            )
            
            # Update constituent download status
            execute_command(
                """
                UPDATE sp500_constituents 
                SET download_status = 'error'
                WHERE symbol = %s
                """,
                (symbol,),
                config
            )
            
            return 0, error_msg
    
    # Should never reach here, but just in case
    return 0, "Max retries exceeded"


def _log_download(
    symbol: str,
    start_date: str,
    end_date: str,
    bars: int,
    status: str,
    error_message: Optional[str],
    download_start: datetime,
    batch_id: Optional[str],
    config: Optional[DatabaseConfig],
) -> None:
    """Log download to database."""
    duration = (datetime.utcnow() - download_start).total_seconds()
    
    execute_command(
        """
        INSERT INTO download_log 
            (timestamp, batch_id, symbol, start_date, end_date, 
             bars_downloaded, status, error_message, duration_seconds)
        VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (batch_id, symbol, start_date, end_date, bars, status, error_message, duration),
        config
    )


def download_all_sp500(
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    config: Optional[DatabaseConfig] = None,
    skip_existing: bool = False,
    delay_seconds: float = 5.0,
) -> dict[str, int]:
    """
    Download historical data for all S&P 500 constituents.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (default: 2015-01-01)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        config: Database configuration (optional)
        skip_existing: Skip symbols that already have data (default: False)
        delay_seconds: Delay between downloads to avoid rate limiting (default: 1.0)
    
    Returns:
        Dictionary with download statistics
    
    Example:
        >>> stats = download_all_sp500(start_date="2020-01-01", delay_seconds=2.0)
        >>> print(f"Downloaded {stats['success']} symbols successfully")
        >>> print(f"Failed: {stats['failed']}")
    """
    batch_id = str(uuid.uuid4())
    
    print(f"\n{'='*60}")
    print(f"📊 S&P 500 Historical Data Download")
    print(f"{'='*60}")
    print(f"Batch ID: {batch_id}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date or 'today'}")
    print(f"Delay: {delay_seconds}s between downloads")
    print(f"{'='*60}\n")
    
    # Get list of symbols
    symbols_df = query_to_dataframe(
        "SELECT symbol FROM sp500_constituents WHERE is_active = TRUE ORDER BY symbol",
        config=config
    )
    symbols = symbols_df["symbol"].tolist()
    
    print(f"📋 Found {len(symbols)} S&P 500 constituents\n")
    
    stats = {
        "total": len(symbols),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "total_bars": 0,
    }
    
    for i, symbol in enumerate(tqdm(symbols, desc="Downloading", unit="symbol")):
        # Download (with incremental logic inside download_symbol_data)
        # Note: skip_existing parameter in download_all_sp500 is deprecated,
        # incremental downloads now happen automatically in download_symbol_data
        bars, error = download_symbol_data(
            symbol, 
            start_date, 
            end_date, 
            batch_id, 
            config, 
            skip_existing=True  # Always use incremental downloads
        )
        
        if error:
            stats["failed"] += 1
            tqdm.write(f"❌ {symbol}: {error}")
            
            # If rate limited, increase delay
            if "rate limit" in error.lower() or "too many requests" in error.lower():
                tqdm.write(f"⚠️  Rate limited! Pausing for {delay_seconds * 2}s...")
                time.sleep(delay_seconds * 2)
        elif bars == 0:
            # Already up to date, no new data to download
            stats["skipped"] += 1
            tqdm.write(f"⏭️  {symbol}: Already up to date")
        else:
            stats["success"] += 1
            stats["total_bars"] += bars
            tqdm.write(f"✅ {symbol}: {bars} bars")
        
        # Delay between downloads (except for last one)
        if i < len(symbols) - 1:
            time.sleep(delay_seconds)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 Download Complete")
    print(f"{'='*60}")
    print(f"Total symbols: {stats['total']}")
    print(f"✅ Success: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⏭️  Skipped: {stats['skipped']}")
    print(f"📊 Total bars: {stats['total_bars']:,}")
    print(f"{'='*60}\n")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download S&P 500 data from yfinance")
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
        "--update-constituents",
        action="store_true",
        help="Update S&P 500 constituents first"
    )
    parser.add_argument(
        "--symbol",
        help="Download single symbol only"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip symbols that already have data"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between downloads (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    try:
        # Update constituents if requested
        if args.update_constituents:
            update_sp500_constituents()
            print()
        
        # Download data
        if args.symbol:
            print(f"Downloading {args.symbol}...")
            bars, error = download_symbol_data(
                args.symbol, 
                args.start_date, 
                args.end_date,
                skip_existing=True
            )
            if error:
                print(f"❌ Error: {error}")
                sys.exit(1)
            else:
                print(f"✅ Downloaded {bars} bars for {args.symbol}")
        else:
            stats = download_all_sp500(
                start_date=args.start_date,
                end_date=args.end_date,
                skip_existing=args.skip_existing,
                delay_seconds=args.delay,
            )
            
            if stats["failed"] > 0:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

